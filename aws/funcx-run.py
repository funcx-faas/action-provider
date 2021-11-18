import json
import uuid
import time
import boto3
import datetime

from funcx.sdk.client import FuncXClient
from funcx.utils.errors import TaskPending
from globus_sdk import AccessTokenAuthorizer

def now_isoformat():
    return datetime.datetime.now().isoformat()


def lambda_handler(event, context):
    print(event)

    auth = AccessTokenAuthorizer(event['requestContext']['authorizer']['funcx_token'])
    search_auth = AccessTokenAuthorizer(
        event['requestContext']['authorizer']['search_token'])
    openid_auth = AccessTokenAuthorizer(
        event['requestContext']['authorizer']['openid_token'])

    FuncXClient.TOKEN_DIR = '/tmp'
    fxc = FuncXClient(fx_authorizer=auth, search_authorizer=search_auth,
                      openid_authorizer=openid_auth,
                      use_offprocess_checker=False)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('funcx-actions')

    body = json.loads(event['body'])

    action_id = str(uuid.uuid4())
    monitor_by = body['monitor_by'] if 'monitor_by' in body else None
    manage_by = body['manage_by'] if 'manage_by' in body else None

    tasks = {}
    batch = fxc.create_batch()

    for task in body['body']['tasks']:
        print(task)
        batch.add(endpoint_id=task['endpoint'], function_id=task['function'],
                  **task['payload'])

    batch_res = fxc.batch_run(batch)
    print(batch_res)

    # Give it a bit to run and then attempt to get the status
    time.sleep(0.5)

    task_results = json.dumps({task_id: {"result": None} for task_id in batch_res})

    # Find the taskIDs where the results are not yet in
    running_tasks = list(filter(lambda task_id: bool(task_id),
                                [key if not task_results[key][
                                    'result'] else None
                                 for key in task_results.keys()]))

    failure = None
    if running_tasks:
        for task in running_tasks:
            result = None
            try:
                result = fxc.get_result(task)
                print("---->", result, type(result))

            except TaskPending as eek:
                print("Faiulure ", eek)
                result = None
            except Exception as eek2:
                print("Detected an exception: ", eek2)
                failure = str(eek2)
                result = None

            if result:
                task_results[task]['result'] = result

    # If there are running tasks cache them in Tables
    if running_tasks:
        # Create a dynamo record where the primary key is this action's ID
        # Tasks is a dict by task_id and contains the eventual results from their
        # execution. Where there are no more None results then the action is complete
        response = table.put_item(
            Item={
                'action-id': action_id,
                'tasks': json.dumps({task_id: {"result": None} for task_id in batch_res})
            }
        )
        print("Dynamo", response)
        if failure:
            status = "FAILED"
            details = failure
            display_status = failure
            status_code = 200
        else:
            status = "ACTIVE"
            details = None
            status_code = 202
    else:
        # Return the results with a SUCCEEDED status
        status = 'SUCCEEDED'
        display_status = 'Function Results Received'
        status_code = 200

    result = {
        "action_id": action_id,
        'status': status,
        'display_status': display_status,
        'details': details,
        'monitor_by': monitor_by,
        'manage_by': manage_by,
        'start_time': now_isoformat(),
    }

    print("Status result", result)
    return {
        'statusCode': status_code,
        'body': json.dumps(result)
    }
    
