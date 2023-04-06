from globus_automate_flow import GlobusAutomateFlowDef, GlobusAutomateFlow
import json

import globus_automate_client


def flow_def(flow_permissions, endpoint, sum_function, hello_world_function):
    return GlobusAutomateFlowDef(
        title="FuncX Example",
        description="Show how to invoke FuncX",
        visible_to=flow_permissions['flow_permissions'],
        runnable_by=flow_permissions['flow_permissions'],
        administered_by=flow_permissions['flow_permissions'],
        flow_definition={
            "StartAt": "StartSubmission",
            "States": {
                "StartSubmission": {
                    "Type": "Action",
                    "ActionUrl": " https://b6vr4fptui.execute-api.us-east-1.amazonaws.com/test",
                    "ActionScope": "https://auth.globus.org/scopes/b3db7e59-a6f1-4947-95c2-59d6b7a70f8c/action_all",
                    "Parameters": {
                        "tasks": [{
                            "endpoint": endpoint,
                            "function": sum_function,
                            "payload": {
                                "items": [1, 2, 3, 4]
                            }
                        },
                            {
                                "endpoint": endpoint,
                                "function": sum_function,
                                "payload": {
                                    "items": [10, 20, 30, 40]
                                }
                            },
                            {
                                "endpoint": endpoint,
                                "function": hello_world_function,
                                "payload": {}
                            }
                        ]
                    },
                    "Next": "EndSubmission"
                },
                "EndSubmission": {
                    "Type": "Pass",
                    "End": True
                }
            }
        }
    )

from funcx.sdk.client import FuncXClient
fxc = FuncXClient()

def hello_world():
    return "Hello World!"


def funcx_sum(items):
    import time
    time.sleep(15)
    return sum(items)

with open(".automatesecrets", 'r') as f:
    globus_secrets = json.load(f)

native_app_id = "417301b1-5101-456a-8a27-423e71a2ae26"  # Premade native app ID
flows_client = globus_automate_client.create_flows_client(native_app_id)

flow = flow_def(flow_permissions={
    "flow_permissions": [
        "urn:globus:groups:id:5fc63928-3752-11e8-9c6f-0e00fd09bf20"
    ],
    "admin_permissions": [
        "urn:globus:groups:id:5fc63928-3752-11e8-9c6f-0e00fd09bf20"
    ],
},
    endpoint="4b116d3c-1703-4f8f-9f6f-39921e5864df",
    sum_function=fxc.register_function(funcx_sum),
    hello_world_function=fxc.register_function(hello_world))

print(flow.flow_definition)

example_flow = GlobusAutomateFlow.from_flow_def(flows_client,
                                                flow_def=flow)

example_flow.save_flow("example_flow_info.json")
