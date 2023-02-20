import boto3
from botocore.exceptions import ClientError
import os, json, logging
from secrets import randbelow


UNKNOWN_ERROR = {
    "statusCode": 503,
    "body": "Internal failure"
}

UNKNOWN_ROUTE = {
    "statusCode": 404,
    "body": "Not found"
}

SUCCESS_CODE_ADD = {
    "statusCode": 200,
    "body": ""
}

CODE_LENGTH = 20
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
            if e.response['Error']['Code'] == 'NoSuchKey':
                logging.info('First-time setup detected, creating empty codebank')
                file_content = '{"unused_codes": [], "expired_codes": []}'
            else:
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



def generate_random_code():
    charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    charset += 'abcdefghijklmnopqrstuvwxyz'
    charset += '0123456789'
    charset += '_-'
    charset = list(charset)
    
    num_chars = len(charset)
    code = ''

    for _ in range(CODE_LENGTH):
        idx = randbelow(num_chars)
        code += charset[idx]

    return code



## Adds new code to codebank and saves to storage
## Returns HTTP response based on success
def add_new_code(codebank_object):

    codebank = read_write_codebank('read', codebank_object)
    if not codebank:
        return UNKNOWN_ERROR

    ## Generate random code value that doesn't already exist in codebank
    existing_code = True
    while existing_code:
        new_code = generate_random_code()

        if new_code in codebank['expired_codes'] or new_code in codebank['unused_codes']:
            logging.info(f'Generated previously seen code {new_code}, trying again...')

        else:
            logging.info(f'Generated new valid code {new_code}')
            existing_code = False
        

    ## Add new code to codebank and save
    codebank['unused_codes'].append(new_code)
    logging.info(f'Successfully added new code {new_code} to codebank')

    successful_write = read_write_codebank('write', codebank_object, codebank_data=codebank)
    if not successful_write:
        return UNKNOWN_ERROR


    ## Provide new code back in response
    SUCCESS_CODE_ADD['body'] = new_code
    return SUCCESS_CODE_ADD




## Example API usage: <apidomain>.amazonaws.com/generate_code
##
## Codebank format: {'unused_codes': [], 'expired_codes': []}
def lambda_handler(event, _):
    logging.getLogger().setLevel(logging.INFO)

    logging.info(f'Invoked AddCode API with event: {event}')

    ## Expected path: /<version>/generate_code
    path = event['path']
    try:
        version, action = path.split('/')[1:] ## strip off leading /
        if action != 'generate_code':
            return UNKNOWN_ROUTE
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
        logging.error(f'Could not create S3 API client using IAM role, exiting: {e}')
        return UNKNOWN_ERROR

    ## If path and API client are good, time to generate and save code
    return add_new_code(codebank_object)