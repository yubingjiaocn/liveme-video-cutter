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
 
    id = event['id']
    if id == None:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': 'ID is required'})
        }
    print("Delete " + str(id) + " by request")
    table.update_item(Key = {'id': str(id)}, 
                      UpdateExpression = 'SET available = :val1', 
                      ExpressionAttributeValues = {':val1': 0})

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
                            'Src': 'DeleteVideofromDB',
                            'ID': id,
                            'Result': 'DELETED'})
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
