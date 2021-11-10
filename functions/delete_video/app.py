import time
import boto3
import os
import json
from boto3.dynamodb.conditions import Key

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

    response = table.query(KeyConditionExpression=Key('id').eq(str(id)))
    if len(response['Items']) == 0:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': 'ID not exists'})
        }

    if 'delete_method' in response['Items'][0].keys():
        delete_method = response['Items'][0]['delete_method'] + "+API"
        delete_timestamp = response['Items'][0]['delete_timestamp']
    else:
        delete_method = "API"
        delete_timestamp = int(time.time())

    table.update_item(Key={'id': str(id)},
                      UpdateExpression='SET available = :val1, delete_timestamp = :val2, delete_method = :val3',
                      ExpressionAttributeValues={':val1': 0,
                                                 ':val2': delete_timestamp,
                                                 ':val3': delete_method})

    try:
        logs.create_log_stream(logGroupName=LOG_GROUP,
                               logStreamName=LOG_STREAM)
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
