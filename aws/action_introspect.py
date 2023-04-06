import json


def lambda_handler(event, context):
    print(event)

    return {
        'statusCode': 202,
        'body': json.dumps(
            {
                "globus_auth_scope": "https://auth.globus.org/scopes/b3db7e59-a6f1-4947-95c2-59d6b7a70f8c/action_all",
                "title": "FuncX Action Provider",
                "subtitle": "Run FuncX",
                "admin_contact": "bengal1@illinois.edu",
                "synchronous": False,
                "input_schema": {
                    "additionalProperties": False,
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
                },
                "keywords": None,
                "log_supported": False,
                "maximum_deadline": "P30D",
                "runnable_by": [
                    "all_authenticated_users"
                ],
                "types": [
                    "Action"
                ],
                "visible_to": [
                    "public"
                ]
            }
        )
    }