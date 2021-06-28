import os
import time
import boto3
import json
from operator import itemgetter

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Access')

sg = boto3.client('sagemaker-runtime')
endpoint_name = os.environ.get('SG_ENDPOINT')

'''
from elasticsearch import Elasticsearch, RequestsHttpConnection
# Init ES
es_host = os.environ.get('ES_ENDPOINT') 
region = os.environ.get('AWS_REGION') 

es = Elasticsearch(
    hosts = [{'host': es_host, 'port': 443}],
    http_auth = auth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)

es_index = os.environ.get('ES_INDEX') 
'''

def lambda_handler(event, context):
    logcontent = []

    items = event['Records']
    count = len(items)
    print("Sending " + str(count) + " file to inference")

    logcontent.append({
        'timestamp': int(round(time.time() * 1000)),
        'message': json.dumps({
            'Level': 'INFO',
            'Src': 'Inference',
            'BatchCount': count,
            'Result': 'START'})
    })

    batch = []

    for item in items:
        bucket = item['Records'][0]['s3']['bucket']['name']
        video_uri = item['Records'][0]['s3']['object']['key']

        payload = json.dumps({
            'bucket': bucket,
            'video_uri': video_uri
        })

        print('Processing s3://' + bucket + '/' + video_uri)
        #Single file inference
        '''
        response = sg.invoke_endpoint(EndpointName=endpoint_name,
                                      Body=payload,
                                      ContentType='application/json')

        resp = response['Body'].read().decode()
        print(resp)
        #es.index(index = es_index, doc_type = "_doc", body = resp)

        logcontent.append({
            'timestamp': int(round(time.time() * 1000)),
            'message': json.dumps({
                'Level': 'DEBUG',
                'Src': 'Inference',
                'Path': video_uri,
                'Result': resp})
        })
        '''

        #Batch inference
        '''
        batch.append(payload)

    response = sg.invoke_endpoint(EndpointName=endpoint_name,
                                      Body=batch,
                                      ContentType='application/json')

    resp = response['Body'].read().decode()
    print(resp)
    
    logcontent.append({
            'timestamp': int(round(time.time() * 1000)),
            'message': json.dumps({
                'Level': 'DEBUG',
                'Src': 'Inference',
                'Path': 'Batch',
                'Result': resp})
        })
    '''

    logcontent.append({
        'timestamp': int(round(time.time() * 1000)),
        'message': json.dumps({
            'Level': 'INFO',
            'Src': 'Inference',
            'BatchCount': count,
            'Result': 'COMPLETE'})
    })

    print(str(count) + " files inference complete")

    try:
        logs.create_log_stream(logGroupName=LOG_GROUP,
                               logStreamName=LOG_STREAM)
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
