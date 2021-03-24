import json
from funcx.sdk.client import FuncXClient
from globus_sdk import AccessTokenAuthorizer
import boto3


def lambda_handler(event, context):
    print(event)
    name = event['requestContext']['authorizer']['name']
    identities = eval(event['requestContext']['authorizer']['identities'])
    user_id = event['requestContext']['authorizer']['user_id']
    user_email = event['requestContext']['authorizer']['principalId']
    depends = eval(
        event['requestContext']['authorizer']['globus_dependent_token'].replace("null",
                                                                                "None"))
    print(depends['funcx_service'])

    token = depends['funcx_service']['access_token']
    auth = AccessTokenAuthorizer(token)

    search_token = depends['search.api.globus.org']['access_token']
    search_auth = AccessTokenAuthorizer(search_token)

    openid_token = depends['auth.globus.org']['access_token']
    openid_auth = AccessTokenAuthorizer(openid_token)
    FuncXClient.TOKEN_DIR = '/tmp'
    fxc = FuncXClient(fx_authorizer=auth, search_authorizer=search_auth,
                      openid_authorizer=openid_auth)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('funcx-actions')

    body = json.loads(event['body'])
    task = body['body']['tasks'][0]
    print(task)
    res = fxc.run(endpoint_id=task['endpoint'], function_id=task['function'])
    print("Funcx", res)

    response = table.put_item(
        Item={
            'flow-id': body['request_id'],
            'tasks': [
                res
            ]
        }
    )
    print("Dynamo", response)
    return {
        'statusCode': 202,
        'body': json.dumps(
            {
                "result": body['request_id']
            }
        )
    }