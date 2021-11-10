import json
import boto3
import os
import traceback
from es_helper import EsBase
from utils import *

# Init ES
es_host = os.environ.get('ES_ENDPOINT')
region = os.environ.get('AWS_REGION')

es_index = os.environ.get('ES_INDEX')
es = EsBase(es_index)

sg = boto3.client('sagemaker-runtime')
endpoint_name = os.environ.get('SG_ENDPOINT')

def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']
    video_uri = event['Records'][0]['s3']['object']['key']

    payload = json.dumps({
        'bucket' : bucket,
        'video_uri' : video_uri
    })
    uid = video_uri.split('/')[0]

    print('Processing s3://' + bucket + '/' + video_uri)

    response = sg.invoke_endpoint(EndpointName = endpoint_name,
        Body = payload,
        ContentType = 'application/json')

    resp = response['Body'].read().decode()


    result = json.loads(resp)
    result['uid'] = uid
    print (result, type(result))
    query_body = {
        "query": {
            "match": {
                "uid": uid
            }
        }
    }
    try:
        query_result = es.query_one(query_body, source=['uid', 'online_tag'])
        if len(query_result['data']) > 0:
            res_source = query_result['data'][0]['_source']
            if result['score'] == 'is_dancing':
                print("add dance tag for uid = {}".format(uid))
                res = add_onlineTag_dance(res_source)
            elif result['score'] == 'no_dancing':
                print("remove dance tag for uid = {}".format(uid))
                res = remove_onlineTag_dance(res_source)
            else:
                print("unrecognized score = {}".format(result['score']))
            update_result = es.update_one_local({"doc": res}, id=query_result['data'][0]['_id'])
    except:
        traceback.print_exc()

    return {
        "statusCode": 200
    }
