from datetime import datetime, timezone
import logging
import os
from uuid import uuid4

from flask import Flask

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

from provider.config import FXConfig
from provider.schema import FuncXDirectorySchema
from util import FXUtil

ap_description = ActionProviderDescription(
    globus_auth_scope="",            # TODO Update
    admin_contact="lei@globus.org",  # TODO Update with Team contact
    title="FuncX Execution",
    subtitle="Run remote FuncX compute tasks on target endpoint",
    synchronous=True,
    input_schema=FuncXDirectorySchema,
    log_supported=False,
)

provider_bp = ActionProviderBlueprint(
    name="funcx_ap",
    import_name=__name__,
    url_prefix="",
    provider_description=ap_description,
    globus_auth_client_name="",      # TODO Update
)

logger = logging.getLogger(__name__)


def fail_action(action: ActionStatus, err: str) -> ActionStatus:
    error_msg = f"Error: {err}"
    action.status = ActionStatusValue.FAILED
    action.details = ActionFailedDetails(code="Failed", description=error_msg)
    return action


def _fx_worker(
    action: ActionStatus, request: ActionRequest, auth: AuthState
) -> ActionStatus:
    eid = request.body.get("endpoint_uuid")
    fid = request.body.get("function_uuid")
    fn_args_str = request.body.get("function_arguments")

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
                funcx_output = fxc.run(endpoint_id=eid, function_id=fid)
        except Exception as e:
            err = f"Encountered {e} connecting to endpoint {eid}"

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
    return "Unknown", None  # TODO TBD


def get_status(request_id):
    status, action_request = get_status_and_request(request_id)
    return status


def delete_action(request_id):
    assert request_id
    pass  # TODO


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
    status, request = get_status_and_request(action_id)
    if status is None:
        raise ActionNotFound(f"No Action with id {action_id} found")
    authorize_action_management_or_404(status, auth)
    if status.is_complete():
        return status
    else:
        status.status = ActionStatusValue.FAILED
        status.completion_time = FXUtil.iso_tz_now(True)
        status.display_status = f"Cancelled by {auth.effective_identity}"[:64]


@provider_bp.action_release
def action_release(action_id: str, auth: AuthState):
    action, request = get_status(action_id)
    if action is None:
        raise ActionNotFound(f"No Action with id {action_id} found")
    authorize_action_management_or_404(action, auth)

    # action = _update_action_state(action, request, auth)
    if not action.is_complete():
        raise ActionConflict("Action is not complete")

    delete_action(action_id)
    return action


def load_funcx_provider(app: Flask, config: dict = None) -> Flask:
    """
    This is the entry point for the Flask blueprint
    """

    if config is None:
        config = FXConfig.BP_CONFIG

    env_client_id = os.getenv(FXConfig.CLIENT_ID_ENV)
    env_client_secret = os.getenv(FXConfig.CLIENT_SECRET_ENV)

    if env_client_id:
        config["globus_auth_client_id"] = env_client_id
        # TODO figure out why _name is used in auth client_id checking
        config["globus_auth_client_name"] = env_client_id
    else:
        raise EnvironmentError(f"{FXConfig.CLIENT_ID_ENV} needs to be set")

    if env_client_secret:
        config["globus_auth_client_secret"] = env_client_secret
    else:
        raise EnvironmentError(f"{FXConfig.CLIENT_SECRET_ENV} needs to be set")

    provider_bp.url_prefix = config["url_prefix"]

    # TODO change to _name
    provider_bp.globus_auth_client_name = config["globus_auth_client_id"]

    app.config["CLIENT_ID"] = config["globus_auth_client_id"]
    app.config["CLIENT_SECRET"] = config["globus_auth_client_secret"]

    ap_description.globus_auth_scope = config["globus_auth_scope"]
    ap_description.visible_to = config["visible_to"]
    ap_description.runnable_by = config["runnable_by"]
    ap_description.admin_contact = config["admin_contact"]
    ap_description.administered_by = config["administered_by"]

    app.register_blueprint(provider_bp)

    logger.info("SSH Provider loaded successfully")

    return app
