# Serverless Globus Automate Action Provider
This repo contains configuration and code for deploying a serverless Globus
Automate Action Provider for submitting funcX tasks.

## Initial Setup
Create a GlobusAuth app as per the instructions from [Action Provider Tools](https://action-provider-tools.readthedocs.io/en/latest/setting_up_auth.html)

Save the resulting client ID and secret in [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/home?region=us-east-1#!/listSecrets) 
You will want to add two values:
- API_CLIENT_ID
- API_CLIENT_SECRET

The lambda functions here assume that the secret is named `funcX-GlobusAPI`

## Dynamo DB
We use a single DynamoDB table to relate action_id's to taskIDs. 
You will need to create a dynamo DB table called `funcx-actions` - set the
partition key to `action-id` (string). We will need a policy to allow the 
lambda functions to interact with this table. This one should do:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:ConditionCheckItem",
                "dynamodb:PutItem",
                "dynamodb:DeleteItem",
                "dynamodb:PartiQLUpdate",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "dynamodb:DescribeTimeToLive",
                "dynamodb:PartiQLSelect",
                "dynamodb:DescribeTable",
                "dynamodb:PartiQLInsert",
                "dynamodb:GetItem",
                "dynamodb:UpdateTable",
                "dynamodb:PartiQLDelete"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:512084481048:table/funcx-actions"
        }
    ]
}
```

The `Resource` ARN should match the table you created.

An example of the items in this table looks like this:
```json
{
  "action-id": "e9e664d2-d923-4c48-948d-d9b68145077c",
  "tasks": {
    "5d6ae875-ef80-44eb-8664-4c159ced0c46": {
      "result": "Hello World!"
    },
    "86017ef8-faaa-4f50-af62-44d1cf02398e": {
      "result": 10
    },
    "f2ccbd80-e94b-4af0-afad-f35aff58d4c4": {
      "result": 100
    }
  }
}
```

Action-id is the partition key and matches the GlobusAutomate action that was received
by the service. Tasks is a dictionary of taskID to the results returned from the
function invocation. The `result` is null until something comes back from funcX.

When all of the results are non-null the action is complete.
 
 
## Lambda Functions
The lambda functions implement the Action Provider API. They are automatically
deployed to the AWS account by github actions. 

All of the functions get their dependencies from an AWS Lambda Layer called 
`FuncxLayer` which is built from [aws/requirements.txt](aws/requirements.txt).

The action provider functions are fronted by an authorizer function called
`funcx-globus-auth` - This introspect's the bearer token and extracts the 
needed dependent tokens. It adds some useful extracted data to the event dict
passed into each lambda function. 

```python
    authResponse['context'] = {
        'name': name,
        'user_id': user_id,
        'identities': str(identities),
        'funcx_token': funcx_token,
        'search_token': search_token,
        'openid_token': openid_token
    }
```

The GitHub Action CI job that deploys these Lambda functions assumes that the 
AWS credentials are stored in repository secrets:
* AWS_ACCESS_KEY_ID
* AWS_SECRET_ACCESS_KEY 

I think th GitHubAction assumes that the layer, and the lambda functions already 
exist in the account, so you may need to create initial blank values for these.

## API Gateway
The key to the serverless architecture is the AWS API Gateway. Ideally this 
would be configured by a CloudFormation template, however for now, these
notes will have to do.

1. Go to [API Gateway dashboard](https://console.aws.amazon.com/apigateway/main/apis?region=us-east-1) 
in the AWS Console.
2. Create new REST API. Use _New API_ since I haven't had luck importing the OpenAPI Spec
3. Click on _Authorizers_ and create a new lambda authorizer based on [aws/funcx-globus-auth.py](aws/funcx-globus-auth.py)
4. For _Lambda Event Payload_ select _Request_ and use `Header: Authorization` - this
takes the bearer token and puts it into the `event` dict.
5. Now go into _Resources_ and add a GET method under `/` 
6. Set up as _Lambda Function_ Integration Type
7. Check _Use Lambda Proxy integration_
8. Select [aws/action_introspect](aws/action_introspect.py) 
9. Add a resource named `/run` and add a POST method
10. Select [aws/funcx-run](aws/funcx-run.py) as the lambda function
11. Make a new resource called `action_id` and set the path to be `{action_id}` -
this will create a path variable.
12. Under action_id, create a new resource called `status` and add a GET method
which calls `action-status` Lambda
13. Finally select _Deploy API_ action and create a new stage called `dev` - make
a note of the generated URL

## Interacting with The Action Provider
You will need to install the Globus Automate cli 
```shell script
pip install globus_automate_client
```

### View the action
You can retrieve the action document with:
```shell script
 globus-automate action introspect --action-url <<URL From Gateway>> --action-scope <<Scope from Globus Auth>>
```

## Run the Action in Isolation
You need to create a body json document that represents an invocation of the action.
```json
{
	"tasks": [{
		"endpoint": "4b116d3c-1703-4f8f-9f6f-39921e5864df",
		"function": "4b116d3c-1703-4f8f-9f6f-39921e5864df",
		"payload": {
			"x": 2
		}
	}]
}
```

Then invoke the action with
```shell script
globus-automate action run --body sample.json --action-url <<URL From API Gateway>> --action-scope <<Scope from Globus Auth>>
```

## Deploy the Example Flow
Examine the code in [example/deploy_example_flow.py](example/deploy_example_flow.py) 
- this will create a flow definition that invokes the action provider. You'll 
need to update the `ActionUrl` and `ActionScope` to match your new ActionProvider.

Note the generated Flow ID. You can launch an instance of this flow with  
```shell script
 globus-automate flow run -v <<your flow ID>>
```

Note the flow_id that comes back so you can monitor the progress with
```shell script
globus-automate flow action-status -v --flow-id <<your flow ID>> <<your action ID>>
```
