import json
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import os
'''
# Init ES
es_host = os.environ.get('ES_ENDPOINT') 
region = os.environ.get('AWS_REGION') 

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

es = Elasticsearch(
    hosts = [{'host': es_host, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)

es_index = os.environ.get('ES_INDEX') 
'''

sg = boto3.client('sagemaker-runtime')
endpoint_name = os.environ.get('SG_ENDPOINT') 

def lambda_handler(event, context):

    bucket = event['Records'][0]['s3']['bucket']['name']
    video_uri = event['Records'][0]['s3']['object']['key']

    payload = json.dumps({
        'bucket' : bucket,
        'video_uri' : video_uri
    })

    print('Processing s3://' + bucket + '/' + video_uri)

    response = sg.invoke_endpoint(EndpointName = endpoint_name,
        Body = payload,
        ContentType = 'application/json')

    resp = response['Body'].read().decode() 

#    resp = '{\'score\': \'success\'}'

    print (resp)

#    es.index(index = es_index, doc_type = "_doc", body = resp)

    return {
        "statusCode": 200        
    }
