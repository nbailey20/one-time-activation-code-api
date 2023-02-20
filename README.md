# AWS-Hosted One-Time Activation Code Generation & Validation APIs

## Latest Version: 1.0.3

# Release Notes
## v1.0.3
* Updated: 2/20/23
* Updated API logic to support versions in URL path, so you can have a code for offline mode vs online mode separately
* Blocked public access to S3 bucket so people can't bypass API even if they somehow knew the S3 bucket name

## v1.0.2
* Updated: 7/12/22
* Locking down API to IAM user instead of IP for actual security

## v1.0.1
* Updated: 4/20/22
* Split into 2 APIs: one public, one locked down to specific IP address

## v1.0.0
* Initial working POC, single API with multiple routes


# Usage Instructions
* Create CloudFormation stack with uploaded create_api.yml template, enter desired parameters, acknowledge creation of IAM resources
* Create access credentials for new user in IAM service and save locally with "aws configure" command in command prompt (requires AWS CLI)
* Use access credentials to invoke AddCode API, 'python test_app.py' for example invocation
* Invoke CheckCode API with code from AddCode response, should be Valid code: expected path is: hostname/v1/versionname/code
* To delete/recreate, first empty all files from S3 bucket, then delete stack
* If recreating brand new, API invoke URL will change! Rotate credentials from IAM service if needed