import json
from funcx.sdk.client import FuncXClient
from globus_sdk import AccessTokenAuthorizer
import boto3
import uuid
import datetime


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
                      openid_authorizer=openid_auth)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('funcx-actions')

    body = json.loads(event['body'])

    action_id = str(uuid.uuid4())
    monitor_by = body['monitor_by'] if 'monitor_by' in body else None
    manage_by = body['manage_by'] if 'manage_by' in body else None

    result = {
        "action_id": action_id,
        'status': 'ACTIVE',
        'display_status': 'Function Submitted',
        'details': None,
        'monitor_by': monitor_by,
        'manage_by': manage_by,
        'start_time': now_isoformat(),
    }
    tasks = {}
    batch = fxc.create_batch()

    for task in body['body']['tasks']:
        print(task)
        batch.add(endpoint_id=task['endpoint'], function_id=task['function'],
                  **task['payload'])

    batch_res = fxc.batch_run(batch)
    print(batch_res)

    # Create a dynamo record where the primary key is this action's ID
    # Tasks is a dict by task_id and contains the eventual results from their
    # execution. Where there are no more None results then the action is complete
    response = table.put_item(
        Item={
            'action-id': action_id,
            'tasks': {task_id: {"result": None} for task_id in batch_res}
        }
    )
    print("Dynamo", response)
    return {
        'statusCode': 202,
        'body': json.dumps(result)
    }