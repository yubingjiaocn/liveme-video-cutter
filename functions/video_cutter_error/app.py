import time
import boto3
import os
import json

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Error')

def lambda_handler(event, context):
    id = event["requestPayload"]["id"]
    url = event["requestPayload"]["url"]

    error_log = event["responsePayload"]["errorMessage"]

    try:
       logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except logs.exceptions.ResourceAlreadyExistsException:
       pass
    
    for attempt in range(3):
        try:
            response = logs.describe_log_streams(
                logGroupName=LOG_GROUP,
                logStreamNamePrefix=LOG_STREAM
            )
            
            if 'uploadSequenceToken' in response['logStreams'][0]:
                token = response['logStreams'][0]['uploadSequenceToken']
            else:
                token = "0"
                
            response = logs.put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=LOG_STREAM,
                logEvents=[
                    {
                        'timestamp': int(round(time.time() * 1000)),
                        'message': json.dumps({
                            'Level': 'ERROR',
                            'Src': 'VideoCutter',
                            'ID': id,
                            'URL': url,
                            'Msg': error_log,
                            'Result': 'FAILED'})
                    }
                ],
                sequenceToken=token
            )
        except logs.exceptions.InvalidSequenceTokenException:
            continue
        break

    return {
        "statusCode": 200
    }
