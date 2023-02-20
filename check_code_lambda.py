import boto3
from botocore.exceptions import ClientError
import os, json, logging



INVALID_DOWNLOAD_CODE = {
    "statusCode": 403,
    "body": "Invalid download code."
}

EXPIRED_DOWNLOAD_CODE = {
    "statusCode": 405,
    "body": "Expired download code."
}

VALID_DOWNLOAD_CODE = {
    "statusCode": 201,
    "body": "Valid download code."
}

UNKNOWN_ROUTE = {
    "statusCode": 404,
    "body": "Not found"
}

UNKNOWN_ERROR = {
    "statusCode": 503,
    "body": "Internal failure."
}


CODEBANK_FILE_SUFFIX = 'codebank.json'


## Wrapper around AWS library methods to read/write to/from file in storage using provided API client
## If no codebank exists (first execution), create new one
## Returns codebank if action == read, otherwise False
## If action == write, returns True or False depending on success
def read_write_codebank(action, s3_object, codebank_data=None):

    if action == 'read':
        ## Get object from storage
        try:
            res = s3_object.get()
            file_content = res['Body'].read().decode('utf-8')
            logging.info('Successfully retrieved codebank from storage')

        except ClientError as e:
            logging.error(f'Could not retrieve codebank, exiting: {e}')
            return False
        
        ## Load object content
        try:
            codebank = json.loads(file_content)
            logging.info('Successfully parsed codebank')
            return codebank

        except:
            logging.error('Could not read codebank, exiting')
            return False


    elif action == 'write':
        ## Write object back to storage
        try:
            s3_object.put(
                Body=(bytes(json.dumps(codebank_data).encode('utf-8')))
            )
            logging.info('Successfully wrote updated codebank to storage')
            return True

        except ClientError as e:
            logging.error(f'Could not write codebank to storage, exiting: {e}')
            return False



## Changes codebank code from unused to expired, 
## Returns False if code already expired, otherwise updated codebank
def expire_used_code(codebank, code):
    if code in codebank['expired_codes']:
        logging.info(f'Code {code} is already expired, aborting')
        return False

    codebank['expired_codes'].append(code)
    codebank['unused_codes'].remove(code)
    logging.info(f'Changing code {code} to expired')
    return codebank



## Checks provided code against unused_codes in codebank and sets value to expired if match
## Returns appropriate HTTP response for given code
def check_code(input_code, codebank_object):
    codebank = read_write_codebank('read', codebank_object)

    if input_code in codebank['expired_codes']:
        return EXPIRED_DOWNLOAD_CODE

    if input_code in codebank['unused_codes']:
        updated_codebank = expire_used_code(codebank, input_code)

        if not updated_codebank:
            return UNKNOWN_ERROR

        read_write_codebank('write', codebank_object, codebank_data=updated_codebank)
        return VALID_DOWNLOAD_CODE

    return INVALID_DOWNLOAD_CODE



## Example API usage: <apidomain>.amazonaws.com/12345 to validate code '12345'
##
## Codebank format: {'unused_codes': [], 'expired_codes': []}
def lambda_handler(event, _):
    logging.getLogger().setLevel(logging.INFO)

    logging.info(f'Invoked CheckCode API with event: {event}')

    ## Expected path: /<version>/<inputcode>
    path = event['path']
    try:
        version, input_code = path.split('/')[1:] ## strip off leading /
    except:
        logging.error(f'Received unexpected URL path, exiting: {path}')
        return UNKNOWN_ROUTE

    ## Get environment variables needed for script
    try:
        bucket = os.environ['download_bucket']
    except:
        logging.error('Could not retrieve environment variables needed for script, exiting')
        return UNKNOWN_ERROR
    

    ## Create AWS storage API client with Lambda user creds to interact with codebank/game files
    codebank_name = f'{version}-{CODEBANK_FILE_SUFFIX}'
    try:
        s3 = boto3.resource('s3')
        codebank_object = s3.Object(bucket, codebank_name)

    except ClientError as e:
        logging.error(f'Could not create S3 bucket resource using IAM role, exiting: {e}')
        return UNKNOWN_ERROR

    ## If path and API client are good, check input code
    http_response = check_code(input_code, codebank_object)
    logging.info(f'Sending HTTP response {http_response}, script complete.')
    return http_response