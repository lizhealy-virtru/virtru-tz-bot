# How to setup lambda functions
We need to set up two lambda function as we have two endpoints that are hit. We will call our functions neverzone-message and neverzone-action

Setting up each function follows the same process:

## Create the Lambda Function
- Create a new lambda function
- Name it
- Use python 3.7
- Create a new role with basic permissions (idk that much about roles - it's possible this is not necessary and you can use an existing role)
- Create function

## Setting Up Endpoint
- Go to Designer
- Add trigger
- API Gateway
    - Create an API
    - REST API
    - Security: Open
    - Deployment stage: default (or whatever)
    - I did not enable metrics and error logging (I read something that said it throws errors so I didn't - not sure if you should or not)

- We will use the API endpoint as the request_url in Slack
    - For neverzone-message its under event subscriptions
    - For neverzone-action its under interactivity
    - Setting a request_url for event subscriptions in slack requires passing a challenge -- to do so copy the code from the slack_url_setup function in slack_message_resp.py or slack_button_resp.py and paste it into the body of the lambda hander, save, paste neverzone-message API endpoint as request_url and hit verify
    - For setting interactivity request_url you just need to paste neverzone-action api endpoint

## Set up environment variables
- All can be found on slack app admin
- SLACK_SIGNING_SECRET (under Basic Information)
- SLACK_BOT_TOKEN (under OAuth and Permissions)
- SLACK_BOT_ID (In the slack workspace, click on Neverzone, go to profile, click (...) More, copy Member Id)

## Upload deployment package
- We're going to upload the code as a zip
- There are zip files in the repo [neverzone-message → messageDeploymentPackage.zip, neverzone-action → actionDeploymentPackage.zip] if you do not want to edit the code, you can directly upload these, just skip to the upload instruction below. If you made changes, or want to make your own deployment packages, follow the following instructions
    - Go into the folder of the function youre working on [for neverzone-message → lambda_message, for neverzone-action → lambda_action]
    - Run `pip3 install -r requirements.txt -t ./`
    - `zip -r ../myDeploymentPackage.zip .`
    - `cd ..`
    - `unzip -l myDeploymentPackage.zip` to check the contents of the zip
- On the function page, under function code, click Actions -> upload .zip file, select the deployment package zip, save
- We need to change the handler so it points to the lambda handler
    - On the function page, under basic information, click edit
    - For neverzone-message, change handler to slack_message_resp.lambda_handler
    - For neverzone-action, change handler to slack_button_resp.lambda_handler

## Now our lambda function is all set up!
Repeat this process for the other function.


    









