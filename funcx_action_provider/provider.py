from datetime import datetime, timezone
import logging
import os
from typing import Tuple, Optional
from uuid import uuid4

from flask import Flask, request

from funcx.sdk.client import FuncXClient
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
from globus_action_provider_tools.flask.exceptions import ActionConflict, ActionNotFound

from .config import FXConfig
from .util import FXUtil
from .logs import init_logging, log_request_time, set_request_info_for_logging

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
    error_msg = f"Error: {err}"
    action.status = ActionStatusValue.FAILED
    action.details = ActionFailedDetails(code="Failed", description=error_msg)
    return action


def _fx_worker(
    action: ActionStatus, request: ActionRequest, auth: AuthState
) -> ActionStatus:
    body = request.body.copy()
    eid = request.body.get("endpoint")
    fid = request.body.get("function")
    fn_args_str = request.body.get("payload")

    action.status = ActionStatusValue.SUCCEEDED
    start_time = datetime.now()
    err = None
    funcx_output = None

    if eid and fid:
        try:
            if not FXUtil.verify_uuid(eid):
                err = FXConfig.ERR_INVALID_ENDPOINT
            elif not FXUtil.verify_uuid(fid):
                err = FXConfig.ERR_INVALID_FUNCTION
            else:
                fxc = FuncXClient()
                result_id = fxc.run(fn_args_str, endpoint_id=eid, function_id=fid)
                funcx_output = fxc.get_result(result_id)
        except Exception as e:
            err = f"Encountered error connecting to endpoint {eid}: {e}"

        if err is None:
            action.details = {"funcx_output": funcx_output}
        else:
            action.status = ActionStatusValue.FAILED
    else:
        err = FXConfig.ERR_MISSING_INPUT

    if err is None and action.status == ActionStatusValue.SUCCEEDED:
        action.completion_time = FXUtil.iso_tz_now()
        duration = datetime.now() - start_time
        action.details["execution_time_ms"] = duration.microseconds // 1000
    else:
        fail_action(action, err)

    return action


def get_status_and_request(request_id):
    assert request_id
    # Placeholder
    status = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        display_status=ActionStatusValue.ACTIVE,
        start_time=FXUtil.iso_tz_now(),
        completion_time=None,
        creator_id=None,
        monitor_by=None,
        manage_by=None,
        details={},
    )
    return status, None


def get_status(request_id):
    status, action_request = get_status_and_request(request_id)
    return status


def delete_action(request_id):
    assert request_id
    pass  # TODO


def _check_dependent_scope_present(
    request: ActionRequest, auth: AuthState
) -> Optional[str]:
    """return a required dependent scope if it is present in the request,
    and we cannot get a token for that scope via a dependent grant.

    """
    required_scope = request.body.get("required_dependent_scope")
    if required_scope is not None:
        authorizer = auth.get_authorizer_for_scope(required_scope)
        if authorizer is None:
            # Missing the required scope, so return the required scope string
            return f"{ap_description.globus_auth_scope}[{required_scope}]"
    return None


def _update_action_state(
    action: ActionStatus, request: ActionRequest, auth: AuthState
) -> ActionStatus:
    if action.is_complete():
        return action

    required_scope = _check_dependent_scope_present(request, auth)
    if required_scope is not None:
        action.status = ActionStatusValue.INACTIVE
        action.details = ActionInactiveDetails(
            code="ConsentRequired",
            description=f"Consent is required for scope {required_scope}",
            required_scope=required_scope,
        )
    else:
        action = _fx_worker(action, request, auth)

    action.display_status = action.status
    return action


@provider_bp.action_status
def action_status(action_id: str, auth: AuthState):
    action, request = get_status_and_request(action_id)
    if action:
        authorize_action_access_or_404(action, auth)

        # action = _update_action_state(action, request, auth)
        # save_action(action, request=request)
        return action
    else:
        raise ActionNotFound(f"No Action with id {action_id} found")


@provider_bp.action_cancel
def action_cancel(action_id: str, auth: AuthState):
    raise ActionNotFound(f"Action with id {action_id} could not be cancelled")


@provider_bp.action_run
def run_action(request: ActionRequest, auth: AuthState) -> Tuple[ActionStatus, int]:
    status = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        display_status=ActionStatusValue.ACTIVE,
        start_time=FXUtil.iso_tz_now(),
        completion_time=None,
        creator_id=auth.effective_identity,
        monitor_by=request.monitor_by,
        manage_by=request.manage_by,
        details={},
    )

    status = _update_action_state(status, request, auth)
    return status, 202


@provider_bp.action_release
def action_release(action_id: str, auth: AuthState):
    if action_id != 'abc_123_fake':
        raise ActionNotFound(f"No Action with id {action_id} found to release")
    action, request = get_status(action_id)
    if action is None:
        raise ActionNotFound(f"No Action with id {action_id} found")
    authorize_action_management_or_404(action, auth)

    # action = _update_action_state(action, request, auth)
    if not action.is_complete():
        raise ActionConflict("Action is not complete")

    delete_action(action_id)
    return action


@provider_bp.before_request
def before_request():
    set_request_info_for_logging()
    logger.info(f">>>>> ({request.path})")
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_header = auth_header[7:]
    print(f">>>>>DELETE ME {auth_header}")
    if 'POST' == str(request.method):
        logger.info(f"BODY: ({request.get_data()})")


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

    env_client_secret = os.getenv(FXConfig.CLIENT_SECRET_ENV)

    if env_client_secret:
        config["globus_auth_client_secret"] = env_client_secret
    elif not config.get("globus_auth_client_secret"):
        raise EnvironmentError(f"{FXConfig.CLIENT_SECRET_ENV} needs to be set")

    init_logging(log_level='DEBUG')

    provider_bp.url_prefix = config["url_prefix"]

    provider_bp.globus_auth_client_name = config["globus_auth_client_id"]

    app.config["CLIENT_ID"] = config["globus_auth_client_id"]
    app.config["CLIENT_SECRET"] = config["globus_auth_client_secret"]

    logger.info(
        f"CID({FXUtil.sanitize(app.config['CLIENT_ID'])}) "
        f"CSE({FXUtil.sanitize(app.config['CLIENT_SECRET'])})"
    )

    app.register_blueprint(provider_bp)

    if FXConfig.LOG_METHODS:
        for p in app.url_map.iter_rules():
            print(f"{p.methods} ---> {p}")
    return app
