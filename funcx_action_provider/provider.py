from datetime import datetime, timezone
from flask import g
import logging
import time
from traceback import format_exc
from typing import Tuple, Optional, Union

from flask import Flask, request

from funcx.sdk.client import FuncXClient
from funcx.errors import (
    FuncxTaskExecutionFailed,
    SerializationError,
    TaskPending,
)
# from funcx_common.tasks.constants import TaskState, ActorName
from globus_action_provider_tools import AuthState
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
    ActionFailedDetails,
    ActionProviderDescription,
    ActionRequest,
    ActionStatus,
    ActionStatusValue,
)
from globus_action_provider_tools.flask.apt_blueprint import ActionProviderBlueprint
from globus_action_provider_tools.flask.exceptions import (
    ActionConflict,
    ActionNotFound,
    BadActionRequest,
)
from globus_sdk.exc.api import GlobusAPIError
from globus_sdk.scopes import AuthScopes, SearchScopes

from .config import FXConfig
from .config import TaskState, ActorName # TODO replace with fx_common version
from .util import FXUtil
from .logs import init_logging, log_request_time, set_request_info_for_logging
from .login_manager import FuncXLoginManager
from .task_input import TaskInput

logger = logging.getLogger(__name__)

ap_description = ActionProviderDescription(
    title=FXConfig.BP_CONFIG.get("title"),
    subtitle=FXConfig.BP_CONFIG.get("subtitle"),
    globus_auth_scope=FXConfig.BP_CONFIG.get("globus_auth_scope"),
    admin_contact=FXConfig.BP_CONFIG.get("admin_contact"),
    synchronous=FXConfig.BP_CONFIG.get("synchronous"),
    administered_by=FXConfig.BP_CONFIG.get("administered_by"),
    runnable_by=FXConfig.BP_CONFIG.get("runnable_by"),
    manage_by=FXConfig.BP_CONFIG.get("runnable_by"),
    monitor_by=FXConfig.BP_CONFIG.get("runnable_by"),
    visible_to=FXConfig.BP_CONFIG.get("visible_to"),
    log_supported=FXConfig.BP_CONFIG.get("log_supported"),
    maximum_deadline=FXConfig.BP_CONFIG.get("maximum_deadline"),
    input_schema=FXConfig.INPUT_SCHEMA,
)

provider_bp = ActionProviderBlueprint(
    name="funcx_ap",
    import_name=__name__,
    url_prefix="/",
    provider_description=ap_description,
    globus_auth_client_name="",      # TODO Update
)


def fail_action(action: ActionStatus, err: str) -> ActionStatus:
    action.status = ActionStatusValue.FAILED
    action.details = ActionFailedDetails(code="Failed", description=err)
    logger.warning(err)
    return action


def raise_log(e: Exception) -> None:
    logger.warning(f"ERROR in action: {e}")
    raise e


def initialize_funcx_client(auth: AuthState) -> FuncXClient:
    if hasattr(g, 'funcx_client'):
        return g.funcx_client

    funcx_auth = auth.get_authorizer_for_scope(FuncXClient.FUNCX_SCOPE)
    search_auth = auth.get_authorizer_for_scope(SearchScopes.all)
    openid_auth = auth.get_authorizer_for_scope(AuthScopes.openid)

    # Create a new login manager and use it to create a client
    funcx_login_manager = FuncXLoginManager(
        authorizers={FuncXClient.FUNCX_SCOPE: funcx_auth,
                     SearchScopes.all: search_auth,
                     AuthScopes.openid: openid_auth}
    )

    g.funcx_client = FuncXClient(login_manager=funcx_login_manager)
    return g.funcx_client


def _fx_worker(action_request: ActionRequest, auth: AuthState) -> ActionStatus:
    creator_id = auth.effective_identity
    action = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        display_status=ActionStatusValue.ACTIVE,
        start_time=FXUtil.iso_tz_now(),
        completion_time=None,
        creator_id=creator_id,
        monitor_by=action_request.monitor_by,
        manage_by=action_request.manage_by,
        details={},
    )
    task_inputs = []
    fxc = initialize_funcx_client(auth)
    task_group_id = fxc.session_task_group_id
    user_identity = auth.effective_identity

    try:
        req_body = action_request.body
        if FXConfig.LOG_SENSITIVE_DATA:
            logger.info(f"Incoming request: {req_body}")
        task_inputs = TaskInput.from_request(
            req_body,
            task_group_id,
            user_identity
        )
    except ValueError as e:
        raise_log(BadActionRequest(f"Error parsing input: {e}"))

    for task in task_inputs:
        logger.info(TaskState.AP_RECEIVED, extra=task.logging_info())

    action.status = ActionStatusValue.FAILED
    action.action_id = FXConfig.UNKNOWN_TASK_GROUP_ID
    try:
        task_batch = g.funcx_client.create_batch()
        for task in task_inputs:
            if FXConfig.LOG_SENSITIVE_DATA:
                logger.info(f"Running {task.function_id} on {task.endpoint_id} "
                            f"args ({FXUtil.get_start(str(task.args))}) "
                            f"kwargs ({FXUtil.get_start(str(task.kwargs))})")
            task_batch.add(task.function_id, task.endpoint_id, task.args, task.kwargs)
        result_ids = fxc.batch_run(task_batch)
        logger.info(f"Submitted task group {task_group_id} for {user_identity}")
        FXUtil.store_task_group(task_group_id, result_ids, creator_id)
        action.action_id = FXConfig.TG_PREFIX + task_group_id
        action.status = ActionStatusValue.ACTIVE
        action.details = {FXConfig.TASK_OUTPUT: str(result_ids)}

        if len(result_ids) != len(task_inputs):
            logger.error(f"Submitted {len(task_inputs)} tasks but received "
                         f"{len(result_ids)} task_ids")
        else:
            # Assuming that the order of task_ids is the same as submission
            for i in range(len(task_inputs)):
                task = task_inputs[i]
                task.task_id = result_ids[i]
                logger.info(TaskState.AP_TASK_SUBMITTED, extra=task.logging_info())
    except GlobusAPIError as e:
        err = f"Encountered {e.__class__} ({e}) submitting tasks"
        action.details = {FXConfig.TASK_OUTPUT: err}
        fail_action(action, err)
    except Exception as e:
        err = f"Unexpected exception {e.__class__} ({e}) attempting to execute task"
        action.details = {FXConfig.TASK_OUTPUT: err}
        fail_action(action, err)

    return action


def get_status(request_id: str, auth: AuthState) -> ActionStatus:
    status = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        display_status=ActionStatusValue.ACTIVE,
        creator_id=auth.effective_identity,
        completion_time=None,
        monitor_by={auth.effective_identity},
        manage_by={auth.effective_identity},
        details={},
    )

    if request_id.startswith(FXConfig.TG_PREFIX):
        tg_id = request_id[3:]
        status.action_id = request_id
        fxc = initialize_funcx_client(auth)
        try:
            tg_info = FXUtil.get_task_group_tasks(tg_id)
            status.start_time = FXUtil.iso_time(tg_info.get("start_time"))
            status.creator_id = tg_info.get("creator_id")
            results = {}
            pending = False
            failed = False
            for task_id in tg_info.get("task_ids"):
                try:
                    results[task_id] = fxc.get_result(task_id)
                except TaskPending as e:
                    err_msg = f"Task {task_id} is still pending : {e}"
                    logger.info(err_msg)
                    pending = True
                    results[task_id] = err_msg
                    break
                except (FuncxTaskExecutionFailed, SerializationError) as e:
                    err_msg = f"Task {task_id} error: {e.__class__}"
                    logger.info(err_msg)
                    results[task_id] = format_exc()
                    failed = True
                except Exception as e:
                    err_msg = f"Task {task_id} encountered unexpected {e.__class__}"
                    logger.info(err_msg)
                    results[task_id] = format_exc()
                    failed = True

            extra_logging = {
                "user_id": auth.effective_identity,
                "task_id": FXConfig.NOT_AVAILABLE,
                "task_group_id": tg_id,
                "function_id": FXConfig.NOT_AVAILABLE,
                "endpoint_id": FXConfig.NOT_AVAILABLE,
                "container_id": FXConfig.NOT_AVAILABLE,
                "actor": ActorName.ACTION_PROVIDER,
                "state_time": time.time_ns(),
                "log_type": "task_transition",
            }
            if pending:
                # If still active, Flows will keep calling get_status
                status.display_status = "Task group still active"
                logger.info(TaskState.AP_TASKGROUP_RUNNING, extra=extra_logging)
            elif failed:
                status.status = ActionStatusValue.FAILED
                status.display_status = "At least one task failed"
                logger.info(TaskState.AP_TASKGROUP_ERROR, extra=extra_logging)
            else:
                status.status = ActionStatusValue.SUCCEEDED
                status.display_status = "All tasks completed"
                status.completion_time = FXUtil.iso_tz_now()
                logger.info(TaskState.AP_TASKGROUP_COMPLETED, extra=extra_logging)

            status.details = {
                'result': results
            }
        except ValueError as e:
            raise_log(ActionNotFound(f"Task group {tg_id} not found: {e}"))
    else:
        raise_log(ActionNotFound(f"Request ID {request_id} has an invalid prefix"))

    return status


def delete_action(request_id):
    if request_id.startswith(FXConfig.TG_PREFIX):
        FXUtil.delete_task_group(request_id[len(FXConfig.TG_PREFIX):])
    else:
        raise_log(BadActionRequest(f"Invalid request id {request_id}"))


@provider_bp.action_status
def action_status(action_id: str, auth: AuthState):
    action = get_status(action_id, auth)
    authorize_action_access_or_404(action, auth)
    return action


@provider_bp.action_cancel
def action_cancel(action_id: str, auth: AuthState):
    raise_log(BadActionRequest(f"Action ({action_id}) can not be cancelled"))


@provider_bp.action_run
def run_action(
        action_request: ActionRequest,
        auth: AuthState
) -> Tuple[ActionStatus, int]:
    if auth.effective_identity == FXConfig.PRINT_SPECIFIC_TOKEN:
        print(f">>>>>DELETE ME {auth.bearer_token}")

    return _fx_worker(action_request, auth), 202


@provider_bp.action_release
def action_release(action_id: str, auth: AuthState) -> ActionStatus:
    action = get_status(action_id, auth)
    authorize_action_management_or_404(action, auth)

    if not action.is_complete():
        raise_log(ActionConflict("Action is not complete"))

    delete_action(action_id)
    return action


@provider_bp.before_request
def before_request():
    set_request_info_for_logging()
    logger.info(f">>>>> ({request.path})")
    if FXConfig.LOG_SENSITIVE_DATA and 'POST' == str(request.method):
        logger.info(f"POST body: ({request.get_data()})")


@provider_bp.after_request
def after_request(response):
    log_request_time(response)
    return response


def load_funcx_provider(app: Flask, config: dict = None) -> Flask:
    """
    This is the entry point for the Flask blueprint
    """

    if config is None:
        config = FXConfig.BP_CONFIG

    config["globus_auth_client_secret"] = FXUtil.get_client_secret()

    init_logging(log_level='INFO')

    provider_bp.url_prefix = config["url_prefix"]

    provider_bp.globus_auth_client_name = config["globus_auth_client_id"]

    app.config["CLIENT_ID"] = config["globus_auth_client_id"]
    app.config["CLIENT_SECRET"] = config["globus_auth_client_secret"]

    logger.info(
        f"ClientID({FXUtil.sanitize(app.config['CLIENT_ID'])}) "
        f"ClientSec({FXUtil.sanitize(app.config['CLIENT_SECRET'])})"
    )

    app.register_blueprint(provider_bp)

    FXUtil.init_task_group_cache()

    if FXConfig.LOG_METHODS:
        print("Supported routes: ")
        for p in app.url_map.iter_rules():
            print(f"    {p} : {p.methods}")
    return app
