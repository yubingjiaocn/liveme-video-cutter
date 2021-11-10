import time
import boto3
import os
import json
import ast
from boto3.dynamodb.conditions import Key

tablename = os.environ.get('TABLE_NAME')
task_dict = os.environ.get('TASK_DICT')
task_dict = ast.literal_eval(task_dict)
support_task_set = set(task_dict.keys())

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
    task_names = event.get('task_names', ['video'])

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
    if type(task_names) != list:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': 'TASK_NAMES should be a list'})
        }
    if len(set(task_names).difference(support_task_set)) > 0:
        return {
            "statusCode": 400,
            "body": json.dumps({'message': f'TASK_NAMES only support {support_task_set}'})
        }

    if interval == 0:
        interval = 60

    if duration == 0:
        interval = 10

    response = table.query(KeyConditionExpression=Key('id').eq(str(id)))
    print(response)
    if len(response['Items']) == 0 or (len(response['Items']) > 0 and response['Items'][0]['url'] != url):
        item = {
            'id': id,
            'url': url,
            'interval': interval,
            'duration': duration,
            'last_access': timestamp - interval - 1,
            'itemttl': timestamp + TTL,
            'available': 1
        }
        for task in task_names:
            item[task_dict[task]] = 1

        table.put_item(Item=item)
    else:
        update_exp = 'SET last_access = :val1, itemttl = :val2'
        update_dict = {':val1': timestamp - interval - 1, ':val2': timestamp + TTL}
        index = 3
        for task in task_names:
            update_exp += f', {task_dict[task]}= :val{index}'
            update_dict[f':val{index}'] = 1
            index += 1

        table.update_item(Key={'id': id},
                          UpdateExpression=update_exp,
                          ExpressionAttributeValues=update_dict)

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
                            'task_names': task_names,
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
