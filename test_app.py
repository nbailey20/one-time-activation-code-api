from aws_requests_auth.aws_auth import AWSRequestsAuth
import boto3
import requests

## CHANGE ME TO CORRECT VALUES TO TEST ADDCODE API #########################################################
hostname = ""                         ## Example: <API ID>.execute-api.us-east-1.amazonaws.com, NO /v1/!
user_profile = "one-time-download"    ## profile name created during 'aws configure' command
version = "offline"
#############################################################################################################

session = boto3.Session(profile_name=user_profile)
credentials = session.get_credentials()

print("Starting test script to generate new download code by invoking AddCode API...")
auth = AWSRequestsAuth(aws_access_key=credentials.access_key,
                       aws_secret_access_key=credentials.secret_key,
                       aws_token = credentials.token,
                       aws_host=hostname,
                       aws_region='us-east-1',
                       aws_service='execute-api')

response = requests.get(f'https://{hostname}/v1/{version}/generate_code', auth=auth)
print(response.content.decode('ascii'))