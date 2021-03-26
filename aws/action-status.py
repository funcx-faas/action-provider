import json
import boto3
from boto3.dynamodb.conditions import Key
from globus_sdk import AccessTokenAuthorizer
from funcx.sdk.client import FuncXClient


def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('funcx-actions')

    auth = AccessTokenAuthorizer(event['requestContext']['authorizer']['funcx_token'])
    search_auth = AccessTokenAuthorizer(
        event['requestContext']['authorizer']['search_token'])
    openid_auth = AccessTokenAuthorizer(
        event['requestContext']['authorizer']['openid_token'])

    FuncXClient.TOKEN_DIR = '/tmp'
    fxc = FuncXClient(fx_authorizer=auth, search_authorizer=search_auth,
                      openid_authorizer=openid_auth)

    parameters = event['pathParameters']['proxy']
    (action_id, _) = parameters.split('/')
    response = table.query(
        KeyConditionExpression=Key('action-id').eq(action_id)
    )
    assert "Items" in response
    assert len(response['Items']) == 1

    action_record = response['Items'][0]
    print(action_record)

    # Find the taskIDs where the results are not yet in
    running_tasks = list(filter(lambda task_id: bool(task_id),
                                [key if not action_record['tasks'][key][
                                    'result'] else None
                                 for key in action_record['tasks'].keys()]))

    failure = None
    if running_tasks:
        for task in running_tasks:
            result = None
            try:
                result = fxc.get_result(task)
                print("---->", result)

            except Exception as eek:
                print("Faiulure ", type(eek), eek.args)
                if str(eek) == 'waiting-for-ep':
                    result = None
                else:
                    failure = eek

            if result:
                action_record['tasks'][task]['result'] = result

        update_response = table.update_item(
            Key={
                'action-id': action_id
            },
            UpdateExpression="set tasks=:t",
            ExpressionAttributeValues={
                ':t': action_record['tasks']
            },
            ReturnValues="UPDATED_NEW"
        )

        print(update_response)
        print(failure)
        if failure:
            status = "FAILED"
            details = failure
        else:
            status = "ACTIVE"
        details = None
    else:
        status = "SUCCEEDED"
        details = [str(action_record['tasks'][tt]['result']) for tt in
                   action_record['tasks'].keys()]

    result = {
        "action_id": action_id,
        'status': status,
        'display_status': 'Function Results Received',
        'details': details
    }

    print(event)
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
