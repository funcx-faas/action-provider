from datetime import datetime, timezone
from flask import g
import logging
from traceback import format_exc
from typing import Tuple, Optional, Union

from flask import Flask, request

from funcx.sdk.client import FuncXClient
from funcx.errors import (
    FuncxTaskExecutionFailed,
    SerializationError,
    TaskPending,
)
from globus_action_provider_tools import AuthState
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
    ActionFailedDetails,
    ActionInactiveDetails,
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
    try:
        req_body = action_request.body
        if FXConfig.LOG_SENSITIVE_DATA:
            logger.info(f"Incoming request: {req_body}")
        task_inputs = TaskInput.from_request(req_body)
    except ValueError as e:
        raise_log(BadActionRequest(f"Error parsing input: {e}"))

    action.status = ActionStatusValue.FAILED
    action.action_id = FXConfig.UNKNOWN_TASK_ID
    fxc = initialize_funcx_client(auth)
    try:
        task_batch = g.funcx_client.create_batch()
        for task in task_inputs:
            if FXConfig.LOG_SENSITIVE_DATA:
                logger.info(f"Running {task.function_id} on {task.endpoint_id} "
                            f"args ({FXUtil.get_start(str(task.args))}) "
                            f"kwargs ({FXUtil.get_start(str(task.kwargs))})")
            task_batch.add(task.function_id, task.endpoint_id, task.args, task.kwargs)
        result_ids = fxc.batch_run(task_batch)
        task_group = fxc.session_task_group_id
        logger.info(f"Submitted task group {g.funcx_client.session_task_group_id} "
                    f"for {auth.effective_identity}")
        FXUtil.store_task_group(task_group, result_ids, creator_id)
        action.action_id = FXConfig.TG_PREFIX + task_group
        action.status = ActionStatusValue.ACTIVE
        action.details = {FXConfig.TASK_OUTPUT: str(result_ids)}
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
            if failed:
                status.status = ActionStatusValue.FAILED
                status.display_status = "At least one task failed"
            elif pending:
                status.display_status = "Task group still active"
            else:
                status.status = ActionStatusValue.SUCCEEDED
                status.display_status = "All tasks completed"
                status.completion_time = FXUtil.iso_tz_now()

            status.details = {
                'result': results
            }
        except ValueError as e:
            raise_log(ActionNotFound(f"Task group {request_id} not found: {e}"))
    else:
        raise_log(ActionNotFound(f"Invalid task group {request_id}"))

    return status


def delete_action(request_id):
    if request_id.startswith(FXConfig.TG_PREFIX):
        FXUtil.delete_task_group(request_id)
    else:
        raise_log(BadActionRequest(f"Invalid request id {request_id}"))


def _check_dependent_scope_present(
    action_request: ActionRequest, auth: AuthState
) -> Optional[str]:
    """return a required dependent scope if it is present in the request,
    and we cannot get a token for that scope via a dependent grant.

    """
    required_scope = action_request.body.get("required_dependent_scope")
    if required_scope is not None:
        authorizer = auth.get_authorizer_for_scope(required_scope)
        if authorizer is None:
            # Missing the required scope, so return the required scope string
            return f"{ap_description.globus_auth_scope}[{required_scope}]"
    return None


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
    # action = _fx_worker(action, action_request, auth)
    # status = _update_action_state(status, request, auth)
    return _fx_worker(action_request, auth), 202


@provider_bp.action_release
def action_release(action_id: str, auth: AuthState) -> ActionStatus:
    # if 2 > 1:
    #     raise_log(ActionNotFound(f"No Action ({action_id}) found"))
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
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_header = auth_header[7:]
    if FXConfig.LOG_SENSITIVE_DATA:
        print(f">>>>>DELETE ME {auth_header}")
        if 'POST' == str(request.method):
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

    init_logging(log_level='DEBUG')

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
