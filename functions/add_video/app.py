import time
import boto3
import os

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

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
        }
    )

    return {
        "statusCode": 200        
    }
