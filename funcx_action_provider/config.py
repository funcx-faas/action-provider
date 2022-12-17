class FXConfig:
    CONNECT_TIMEOUT_SECONDS = 10
    ERROR_READ_BYTES = 10000
    OUTPUT_READ_BYTES = 100000

    # Detailed logging TODO turn these off
    LOG_METHODS = True
    LOG_SENSITIVE_DATA = False

    # Environment vars that need to be set for the AP Confidential Client
    CLIENT_SECRET_ENV = 'FUNCX_AP_CLIENT_SECRET'

    APP_NAME = "funcx_action_provider"

    BP_CONFIG = {
        "title": "FuncX Action Provider",
        "subtitle": "Run FuncX",
        "synchronous": False,
        "python_module": "funcx_action_provider.provider",
        "entry_point": "app",

        # Test Client
        # "globus_auth_client_id": "c7c96052-d015-4309-9080-681745b6652c",
        # Actual
        "globus_auth_client_id": "b3db7e59-a6f1-4947-95c2-59d6b7a70f8c",

        # Test Client
        # "globus_auth_client_secret": "N/A",
        "globus_auth_client_secret": "replaced_with_env_CLIENT_SECRET",

        # Test Client
        # "globus_auth_client_name": "c7c96052-d015-4309-9080-681745b6652c@clients.auth.globus.org",
        # Actual
        "globus_auth_client_name": "b3db7e59-a6f1-4947-95c2-59d6b7a70f8c@clients.auth.globus.org",

        # Test Client Scope
        # "globus_auth_scope": "https://auth.globus.org/scopes/c7c96052-d015-4309-9080-681745b6652c/action_all",
        # Actual
        "globus_auth_scope": "https://auth.globus.org/scopes/b3db7e59-a6f1-4947-95c2-59d6b7a70f8c/action_all",

        "maximum_deadline": "P30D",

        # Who can see that this Action Provider is available
        "visible_to": ["all_authenticated_users"],                    # TODO update with "public"

        # Who can use this Action Provider in a flows run
        "runnable_by": ["all_authenticated_users"],                   # TODO update
        "administered_by": ["all_authenticated_users"],               # TODO update
        "admin_contact": "lei514@gmail.com",   # TODO update
        "PREFERRED_URL_SCHEME": "https",
        "url_prefix": "/",
        "log_supported": False,
    }

    INPUT_SCHEMA = {
        "additionalProperties": True,
        "properties": {
            "tasks": {
                "description": "List of tasks to invoke",
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "endpoint": {
                            "description": "UUID of Endpoint where the function is to be run",
                            "type": "string"
                        },
                        "function": {
                            "description": "UUID of the function to be run",
                            "type": "string"
                        },
                        "payload": {
                            "description": "Arguments to function",
                            "type": "object"
                        }
                    }
                }
            }

        },
        "type": "object"
    }

    ERR_MISSING_INPUT = ("endpoint_uuid and At least one function_uuid must "
                         "be provided")
    ERR_INVALID_ENDPOINT = "Unknown FuncX Endpoint UUID:  ({ep_id})"
    ERR_INVALID_FUNCTION = "Unknown FuncX Function UUID:  ({fn_id})"
