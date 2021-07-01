import time
import boto3
import os
import json
from boto3.dynamodb.conditions import Attr

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Error')

THRESHOLD = int(os.environ.get('CB_THRESHOLD'))

def lambda_handler(event, context):
    ids = []
    count = 0

    response = table.scan(ProjectionExpression='#i',
                      ExpressionAttributeNames={'#i': 'id'},
                      FilterExpression=Attr('available').eq(1)
    )
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])
        count += len(data)

    deletecount = count - THRESHOLD 

    for item in data:
        table.update_item(Key={'id': item["id"]},
                      UpdateExpression='SET available = :val1, delete_timestamp = :val3, delete_method = :val4',
                      ExpressionAttributeValues={':val1': 0, ':val3': int(time.time()),
                                                 ':val4': 'CIRCUITBREAKER'})
        ids.extend(item["id"]) 
        deletecount -= 1
        if deletecount <= 0:
            break       
        
    print("Circuit breaker activated, deleted " + str(deletecount) + " live streams")
    print("Deleted IDs:")
    print(json.dumps(ids))

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
                            'Level': 'WARN',
                            'Src': 'CircuitBreaker',
                            'Count': THRESHOLD,
                            'Deleted': count - THRESHOLD,
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
