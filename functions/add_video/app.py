import time
import boto3
import os
import json

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Access')

TTL = int(os.environ.get('DDB_TTL'))

PATTERN = os.environ.get('URL_PATTERN')

def lambda_handler(event, context):
    url = event['url']
    id = event['id']
    interval = int(event['interval'])
    duration = int(event['duration'])
    timestamp = int(time.time())

    if url == None:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': 'URL is required'})
        }

    if url.find(PATTERN) == -1:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': 'URL not match with pattern'})
        } 
        
    if interval == 0: 
        interval = 300

    if duration == 0: 
        interval = 30        

    table.put_item(
        Item={
            'id': id,
            'url': url,
            'interval': interval,
            'duration': duration,
            'last_access': timestamp - interval - 1,
            'itemttl': timestamp + TTL,
            'available': 1
        }
    )

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
                            'Level': 'INFO',
                            'Src': 'AddVideotoDB',
                            'ID': id,
                            'URL': url,
                            'Result': 'SUCCESS'})
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
