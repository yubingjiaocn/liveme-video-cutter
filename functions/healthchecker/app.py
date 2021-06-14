import os
import time
import boto3
import json
import requests
from boto3.dynamodb.conditions import Key, Attr

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)


def lambda_handler(event, context):
    timestamp = int(time.time())
    resp = table.scan(
        FilterExpression = Attr('available').eq(1),
    )
    items = resp['Items']
    for item in items:
        available = 0
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries = 3))
        s.mount('https://', HTTPAdapter(max_retries = 3))

        try:
            r = s.get(item["url"], timeout=2)
            if r.ok:
                print('Check livestream ' + item["id"] + ' OK')
                # Add check on empty m3u8, find an empty one
                available = 1
            else:
                print("Livestream " + item["id"] + ' encounter 404')
        except requests.exceptions.RequestException as e:
            print("Livestream " + item["id"] + ' unable to connect')

        table.update_item(Key = {'id': item["id"]}, 
                          UpdateExpression = 'SET available = :val1', 
                          ExpressionAttributeValues = {':val1': available})

    return {
        "statusCode": 200
    }
