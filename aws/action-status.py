import json
import boto3
import decimal
import traceback

from boto3.dynamodb.conditions import Key
from globus_sdk import AccessTokenAuthorizer
from funcx.sdk.client import FuncXClient
from funcx.utils.errors import TaskPending

from funcx.sdk import VERSION as SDK_VERSION


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    print("---->", SDK_VERSION)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('funcx-actions')
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

    action_id = event['pathParameters']['action-id']

    response = table.query(
        KeyConditionExpression=Key('action-id').eq(action_id)
    )
    assert "Items" in response
    assert len(response['Items']) == 1

    action_record = response['Items'][0]
    print(action_record)

    task_results = json.loads(action_record['tasks'])
    # Find the taskIDs where the results are not yet in
    running_tasks = list(filter(lambda task_id: bool(task_id),
                                [key if not task_results[key][
                                    'completed'] else False
                                 for key in task_results.keys()]))

    status = "SUCCEEDED"
    display_status = "Function Results Received"

    failure = None
    if running_tasks:
        for task in running_tasks:
            result = None
            completed = False
            try:
                result = fxc.get_result(task)
                completed = True
            except TaskPending as eek:
                print("Pending ", eek)
            except Exception as eek2:
                failure = traceback.format_exc()
                result = failure
                print("Detected an exception: ", eek2)
                completed = True
            
            task_results[task]['result'] = result
            task_results[task]['completed'] = completed

        update_response = table.update_item(
            Key={
                'action-id': action_id
            },
            UpdateExpression="set tasks=:t",
            ExpressionAttributeValues={
                ':t': json.dumps(task_results, cls=DecimalEncoder)
            },
            ReturnValues="UPDATED_NEW"
        )

        print("updated_response", update_response)

        if failure:
            print("FAILED ", failure)
            status = "FAILED"
            display_status = "Function Failed"
        else:
            status = "ACTIVE"
            display_status = "Function Active"
            details = None

    # Now check again to see if everything is done
    running_tasks = list(filter(lambda task_id: bool(task_id),
                                [key if not task_results[key][
                                    'completed'] else False
                                 for key in task_results.keys()]))
    if not running_tasks:
        all_res = [task_results[tt]['result'] for tt in
                  task_results.keys()]

        details = {'result': all_res}

        print("List results ->", details)

    result = {
        "action_id": action_id,
        'status': status,
        'display_status': display_status,
        'details': details
    }

    print("Status result", result)
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
