import time
import boto3
import os
import json

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Error')

def lambda_handler(event, context):

    counter = 0
    page = table.scan(ProjectionExpression='#i',
                      ExpressionAttributeNames={'#i': 'id'},
                      Limit=50)

    with table.batch_writer() as batch:
        counter = page["Count"]
        ids = page["Items"]
        #for itemKeys in page["Items"]:
        #    batch.delete_item(Key=itemKeys)

    print(f"Circuit breaker activated, deleted {counter} live streams")
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
                            'DeleteCount': counter,
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
