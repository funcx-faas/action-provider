import json
import boto3
from boto3.dynamodb.conditions import Key
from globus_sdk import AccessTokenAuthorizer
from funcx.sdk.client import FuncXClient


def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('funcx-actions')

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

    parameters = event['pathParameters']['proxy']
    (flow_id, _) = parameters.split('/')
    response = table.query(
        KeyConditionExpression=Key('flow-id').eq(flow_id)
    )
    print(response['Items'][0])
    print(response['Items'][0]['tasks'][0])
    result = None
    try:
        result = fxc.get_result(response['Items'][0]['tasks'][0])
    except Exception as eek:
        result = str(eek)

    print("---->", result)
    # TODO implement
    print(event)
    return {
        'statusCode': 200,
        'body': result
    }
