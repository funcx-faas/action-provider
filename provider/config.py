class FXConfig:
    CONNECT_TIMEOUT_SECONDS = 10
    ERROR_READ_BYTES = 10000
    OUTPUT_READ_BYTES = 100000

    # Environment vars that need to be set for the AP Confidential Client
    CLIENT_ID_ENV = 'FUNCX_AP_CLIENT_ID'
    CLIENT_SECRET_ENV = 'FUNCX_AP_CLIENT_SECRET'

    APP_NAME = "funcx_action_provider"

    BP_CONFIG = {
        "python_module": "funcx_action_provider.provider",
        "entry_point": "app",
        "globus_auth_client_id": "replaced_with_env_CLIENT_ID",
        "globus_auth_client_secret": "replaced_with_env_CLIENT_SECRET",
        "globus_auth_client_name": "FuncX Auth Client",
        "globus_auth_scope": "replace_with_scope_id",
        # Who can see that this Action Provider is available
        "visible_to": [],                    # TODO update with "public"
        # Who can use this Action Provider in a flows run
        "runnable_by": [],                   # TODO update
        "administered_by": [],               # TODO update
        "admin_contact": "lei@globus.org",   # TODO update
        "PREFERRED_URL_SCHEME": "https",
        "url_prefix": "/",
    }

    ERR_MISSING_INPUT = ("endpoint_uuid and At least one function_uuid must "
                         "be provided")
    ERR_INVALID_ENDPOINT = "Unknown FuncX Endpoint UUID:  ({ep_id})"
    ERR_INVALID_FUNCTION = "Unknown FuncX Function UUID:  ({fn_id})"
