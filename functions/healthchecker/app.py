import os
import subprocess
import time
import boto3
import botocore
import requests
import threading
from boto3.dynamodb.conditions import Attr
from requests.adapters import HTTPAdapter

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb', config=botocore.client.Config(max_pool_connections=50))
table = dynamodb.Table(tablename)

def check_livestream(url, id):
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

def lambda_handler(event, context):
    timestamp = int(time.time())
    resp = table.scan(
        FilterExpression = Attr('available').eq(1),
    )
    items = resp['Items']
    print("Checking " + str(len(items)) + " live stream")
    threads = []
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
                   
    return {
        "statusCode": 200
    }
