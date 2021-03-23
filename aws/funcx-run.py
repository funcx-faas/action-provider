import json
from funcx.sdk.client import FuncXClient
from globus_sdk import AccessTokenAuthorizer


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
    print("Auth", auth)
    FuncXClient.TOKEN_DIR = '/tmp'
    fxc = FuncXClient(fx_authorizer=auth, search_authorizer=search_auth,
                      openid_authorizer=openid_auth)
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