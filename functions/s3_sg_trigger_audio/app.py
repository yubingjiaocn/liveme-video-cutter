import json
from elasticsearch import Elasticsearch, RequestsHttpConnection
import boto3
import os
import time
from es_helper import EsBase
from utils import *


# Init ES
es_host = os.environ.get('ES_ENDPOINT')
region = os.environ.get('AWS_REGION')


es_index = os.environ.get('ES_INDEX')
es = EsBase(es_index)


es_index = os.environ.get('ES_INDEX')

sg = boto3.client('sagemaker-runtime')
endpoint_name = os.environ.get('SG_ENDPOINT')


def lambda_handler(event, context):
    start_time = int(time.time() * 1000)
    bucket = event['Records'][0]['s3']['bucket']['name']
    video_uri = event['Records'][0]['s3']['object']['key']

    payload = json.dumps({
        'bucket': bucket,
        'video_uri': video_uri
    })
    uid = video_uri.split('/')[0]
    print("uid = ", uid)
    print('Processing s3://' + bucket + '/' + video_uri)

    response = sg.invoke_endpoint(EndpointName=endpoint_name,
                                  Body=payload,
                                  ContentType='application/json')

    resp = response['Body'].read().decode()

    result = json.loads(resp)
    result['uid'] = uid
    result['time'] = video_uri.split('.')[0].split('_')[1]
    end_time = int(time.time() * 1000)
    print("inference time: ", end_time - start_time, result, type(result))

    print (result, type(result))
    try:
        print("insert es")
        # es.index(index=es_index, doc_type="_doc", body=result, id=uid)
    except:
        pass

    return {
        "statusCode": 200
    }
