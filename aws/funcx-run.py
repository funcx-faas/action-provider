import json
from funcx.sdk.client import FuncXClient
from globus_sdk import AccessTokenAuthorizer


def lambda_handler(event, context):
    print(event)

    token = event['headers']['Authorization'].replace("Bearer ", "")
    auth = AccessTokenAuthorizer(token)
    print("Auth", auth)
    FuncXClient.TOKEN_DIR = '/tmp'
    fxc = FuncXClient(fx_authorizer=auth)
    body = json.loads(event['body'])
    print(body)
    print(body['body'])

    return {
        'statusCode': 202,
        'body': json.dumps(
            {
                "result": body['request_id']
            }
        )
    }