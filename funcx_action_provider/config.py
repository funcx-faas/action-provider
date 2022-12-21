class FXConfig:
    # ms to wait between checking results
    EXECUTION_WAIT_INTERVAL_MS = 500
    # Seconds to wait for function results
    EXECUTION_LOOP_COUNT = 10

    ERROR_READ_BYTES = 10000
    OUTPUT_READ_BYTES = 100000

    # Detailed logging TODO turn these off
    LOG_METHODS = True
    LOG_SENSITIVE_DATA = False

    # Environment vars that need to be set for the AP Confidential Client
    CLIENT_SECRET_ENV = "FUNCX_AP_CLIENT_SECRET"
    AWS_SECRET_ID = "funcx-action-provider-client"
    AWS_REGION = "us-east-1"

    APP_NAME = "funcx_action_provider"

    BP_CONFIG = {
        "title": "FuncX Action Provider",
        "subtitle": "Run FuncX",
        "synchronous": False,
        "python_module": "funcx_action_provider.provider",
        "entry_point": "app",

        "globus_auth_client_id": "b3db7e59-a6f1-4947-95c2-59d6b7a70f8c",
        "globus_auth_client_secret": "replaced_with_env_CLIENT_SECRET",
        "globus_auth_client_name": "b3db7e59-a6f1-4947-95c2-59d6b7a70f8c@clients.auth.globus.org",
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
        "additionalProperties": False,
        "properties": {
            "request_id": {
                "description": "ID of Incoming Request from Flows",
                "type": "string"
            },
            "body": {
                "description": "Body of request",
                "additionalProperties": False,
                "items": {
                    "additionalProperties": False,
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
                                "kwargs": {
                                    "description": "Keyword arguments to function (dict)",
                                    "type": "object"
                                },
                                "args": {
                                    "description": "Arguments to function (tuple)",
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        },
        "type": "object"
    }

    UNKNOWN_TASK_ID = 'unknown_funcx_task'
    TASK_OUTPUT = "task_output"

    ERR_MISSING_INPUT = ("endpoint_uuid and At least one function_uuid must "
                         "be provided")
    ERR_INVALID_ENDPOINT = "Unknown FuncX Endpoint UUID:  ({ep_id})"
    ERR_INVALID_FUNCTION = "Unknown FuncX Function UUID:  ({fn_id})"
    ERR_TIMED_OUT = ("Timed out after waiting for %ds waiting for result" %
                     (EXECUTION_LOOP_COUNT * EXECUTION_LOOP_COUNT // 1000))
