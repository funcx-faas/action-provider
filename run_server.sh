export FUNCX_AP_CLIENT_SECRET=`aws secretsmanager get-secret-value --region=us-east-1 --secret-id funcx-action-provider-client --query SecretString |jq -r | jq -rc '.secret'`
flask run
