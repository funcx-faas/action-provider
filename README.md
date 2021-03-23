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
11. Finally select _Deploy API_ action and create a new stage called `dev` - make
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

## Run the Action
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