from globus_automate_flow import GlobusAutomateFlowDef, GlobusAutomateFlow
import json

import globus_automate_client


def flow_def(flow_permissions):
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
                    "ActionUrl": "https://ippg79abte.execute-api.us-east-1.amazonaws.com/dev",
                    "ActionScope": "https://auth.globus.org/scopes/b3db7e59-a6f1-4947-95c2-59d6b7a70f8c/action_all",
                    "Parameters": {
                        "tasks": [{
                            "endpoint": "4b116d3c-1703-4f8f-9f6f-39921e5864df",
                            "function": "18f8416a-edbd-4f3b-82ef-3c5697a0697a",
                            "payload": {
                                "items": [1, 2, 3, 4]
                            }
                        },
                            {
                                "endpoint": "4b116d3c-1703-4f8f-9f6f-39921e5864df",
                                "function": "18f8416a-edbd-4f3b-82ef-3c5697a0697a",
                                "payload": {
                                    "items": [10, 20, 30, 40]
                                }
                            },
                            {
                                "endpoint": "4b116d3c-1703-4f8f-9f6f-39921e5864df",
                                "function": "74c03996-c4b0-471f-b26b-b596edbf80f9",
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
})
print(flow.flow_definition)

mdf_flow = GlobusAutomateFlow.from_flow_def(flows_client,
                                            flow_def=flow)

mdf_flow.save_flow("mdf_flow_info.json")
