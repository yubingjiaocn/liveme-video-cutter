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

def lambda_handler(event, context):
    url = event['url']
    id = event['id']
    interval = int(event['interval'])
    duration = int(event['duration'])
    timestamp = int(time.time())

    table.put_item(
        Item={
            'id': id,
            'url': url,
            'interval': interval,
            'duration': duration,
            'last_access': timestamp - interval - 1,
            'available': 1
        }
    )

    try:
       logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except logs.exceptions.ResourceAlreadyExistsException:
       pass

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

    return {
        "statusCode": 200
    }
