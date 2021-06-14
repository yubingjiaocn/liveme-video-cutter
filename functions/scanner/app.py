import os
import time
import boto3
import json
import requests
from boto3.dynamodb.conditions import Key, Attr

tablename = os.environ.get('TABLE_NAME')
bucketname = os.environ.get('BUCKET_NAME')
cuttername = os.environ.get('VIDEO_CUTTER_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    timestamp = int(time.time())
    resp = table.scan(
        FilterExpression=Attr('available').eq(1)
    )

    items = resp['Items']
    for item in items:
        lambda_payload = {
            "id": item["id"],
            "url": item["url"],
            "duration": str(int(item["duration"])),
            "bucket": bucketname,
            "prefix": ''
        }

        lambda_client.invoke(FunctionName=cuttername,
                             InvocationType='Event',
                             Payload=json.dumps(lambda_payload))

        print('Start recording livestream ' + item["id"])

        table.update_item(Key={'id': item["id"]},
                          UpdateExpression='SET last_access = :val1',
                          ExpressionAttributeValues={':val1': timestamp})

    return {
        "statusCode": 200
    }
