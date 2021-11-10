import os
import time
import boto3
import json
import requests
from boto3.dynamodb.conditions import Key, Attr

tablename = os.environ.get('TABLE_NAME')
bucketname = os.environ.get('BUCKET_NAME')
cuttername = os.environ.get('VIDEO_CUTTER_NAME')
task_name = os.environ.get('TASK_NAME')
task_name = str(task_name)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)
lambda_client = boto3.client('lambda')

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Access')

TTL = int(os.environ.get('DDB_TTL'))


def lambda_handler(event, context):
    timestamp = int(time.time())

    response = table.scan(
        FilterExpression=Attr('available').eq(1) & Attr(task_name).eq(1),
        ProjectionExpression="id, #u, #d",
        ExpressionAttributeNames={"#u": "url", "#d": "duration"}
    )
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    count = len(data)
    print(f"video cutter length: {count}")
    try:
        logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    try:
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
                    logEvents=[{
                        'timestamp': int(round(time.time() * 1000)),
                        'message': json.dumps({
                            'Level': 'INFO',
                            'Src': 'Video_Scanner',
                            'Count': count})
                    }],
                    sequenceToken=token
                )
            except logs.exceptions.InvalidSequenceTokenException:
                continue
            break
    except:
        pass
    for item in data:
        lambda_payload = {
            "id": item["id"],
            "url": item["url"],
            "duration": str(int(item["duration"])),
            "bucket": bucketname,
            "prefix": '',
            "task_name": task_name

        }

        lambda_client.invoke(FunctionName=cuttername,
                             InvocationType='Event',
                             Payload=json.dumps(lambda_payload))

        print('Start recording livestream ' + item["id"])

        table.update_item(Key={'id': item["id"]},
                          UpdateExpression='SET last_access = :val1, itemttl = :val2',
                          ExpressionAttributeValues={':val1': timestamp, ':val2': timestamp + TTL})

    return {
        "statusCode": 200
    }
