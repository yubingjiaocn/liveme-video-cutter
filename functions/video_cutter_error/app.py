import time
import boto3
import os
import json
import botocore

logs = boto3.client('logs')
LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Error')

tablename = os.environ.get('TABLE_NAME')
dynamodb = boto3.resource('dynamodb', config=botocore.client.Config(max_pool_connections=50))
table = dynamodb.Table(tablename)

def lambda_handler(event, context):
    id = event["requestPayload"]["id"]
    url = event["requestPayload"]["url"]
    request_id = event["requestContext"]["requestId"]
    error_log = event["responsePayload"]["errorMessage"]

    print("Live Stream " + id + '(' + url + ')' + ' failed due to ' + error_log)

    result = "FAILED"

    if error_log.find("returned non-zero exit status") != -1:
        try:
            result = "DELETED"
            table.update_item(Key = {'id': id}, 
              UpdateExpression = 'SET available = :val1', 
              ConditionExpression='#u = :val2',
              ExpressionAttributeNames={'#u': 'url'},
              ExpressionAttributeValues = {':val1': 0, ':val2': url})
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:      
            result = "REPLACED"

    if error_log.find("Task timed out") != -1: 
        try:
            result = "TIMEOUT"
            table.update_item(Key = {'id': id}, 
              UpdateExpression = 'SET available = :val1', 
              ConditionExpression='#u = :val2',
              ExpressionAttributeNames={'#u': 'url'},
              ExpressionAttributeValues = {':val1': 0, ':val2': url})
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:      
            result = "REPLACED"
        
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
                            'Req_ID': request_id,
                            'URL': url,
                            'Msg': error_log,
                            'Result': result})
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
