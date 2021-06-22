import os
import subprocess
import time
import boto3
import botocore
import requests
import threading
import json
from boto3.dynamodb.conditions import Attr
from requests.adapters import HTTPAdapter
from operator import itemgetter, attrgetter

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb', config=botocore.client.Config(max_pool_connections=50))
table = dynamodb.Table(tablename)

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Access')

logcontent = []

deletecount = 0

def check_livestream(url, id):
    global deletecount
    global logcontent

    available = 0
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries = 3))
    s.mount('https://', HTTPAdapter(max_retries = 3))

    try:
        r = s.get(url, timeout=(0.3,1))
        if r.ok:
            #print('Livestream ' + id + ' master playlist OK')
            cmd = 'ffprobe -max_reload 3 -hide_banner -loglevel error ' + url
            try:
                subprocess.run(cmd, shell=True, check=True)
                available = 1
                print('Livestream ' + id + ' playlist OK')
            except subprocess.CalledProcessError: 
                print('Livestream ' + id + ' has invalid media file')
        else:
            print("Livestream " + id + ' master playlist failed (404)')
    except requests.exceptions.RequestException as e:
        print("Livestream " + id + ' master playlist failed (Unable to connect)')
        
    if available == 0:
        table.update_item(Key = {'id': id}, 
                      UpdateExpression = 'SET available = :val1', 
                      ExpressionAttributeValues = {':val1': available})

        logcontent.append({
                'timestamp': int(round(time.time() * 1000)),
                'message': json.dumps({
                    'Level': 'DEBUG',
                    'Src': 'HealthCheck',
                    'ID': id,
                    'URL': url,
                    'Result': 'DELETED'})
            })          

        deletecount += 1           

def lambda_handler(event, context):
    global logcontent
    timestamp = int(time.time())
    resp = table.scan(
        FilterExpression=Attr('available').eq(1),
        ProjectionExpression="id, #u",
        ExpressionAttributeNames={"#u": "url"}
    )
    items = resp['Items']
    count = len(items)
    print("Checking " + str(count) + " live stream")

    threads = []
    logcontent.append({
                'timestamp': int(round(time.time() * 1000)),
                'message': json.dumps({
                    'Level': 'INFO',
                    'Src': 'HealthCheck',
                    'Count': count})
            })

    for item in items:
        print("Start checking " + item["id"])
        try:
            t = threading.Thread(target=check_livestream, args=(item["url"], item["id"]))
            threads.append(t)
            t.start()
        except:
            print("create thread failed on " + item["id"])
    for t in threads:
        t.join() 

    logcontent.append({
                'timestamp': int(round(time.time() * 1000)),
                'message': json.dumps({
                    'Level': 'INFO',
                    'Src': 'HealthCheck',
                    'Deleted': deletecount,
                    'Count': count - deletecount,
                    'Result': 'SUCCESS'})
            })       

    try:
       logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except logs.exceptions.ResourceAlreadyExistsException:
       pass

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
        logEvents=sorted(logcontent, key=itemgetter('timestamp')),
        sequenceToken=token
    )

    return {
        "statusCode": 200
    }
