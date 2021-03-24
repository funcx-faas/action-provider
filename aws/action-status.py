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

    result = None
    try:
        result = fxc.get_result(action_record['tasks'][0]['task_id'])
    except Exception as eek:
        result = str(eek)

    print("---->", result)

    result = {
        "action_id": action_id,
        'status': 'SUCCEEDED',
        'display_status': 'Function Results Received',
        'details': result
    }

    print(event)
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
