import json
import subprocess
import time
import boto3
from botocore.config import Config
import os

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Access')

tablename = os.environ.get('TABLE_NAME')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(tablename)

s3_client = boto3.client('s3', config=Config(
    s3={'addressing_style': 'path', 'signature_version': 's3v4'}))

def lambda_handler(event, context):
    url = event['url']
    id = event['id']
    duration = event['duration']
    bucket = event['bucket']
    prefix = event['prefix'].rstrip('/')
    if prefix != '' :
        prefix = prefix + '/' 
    timestamp = int(time.time())
    filename = str(id) + '_' + str(timestamp)
    vid_filename = filename + '.mp4'
    aud_filename = filename + '.mp3'
    cmd = 'ffmpeg -t ' + duration + ' -i ' + url + ' -vcodec mpeg4 -an /tmp/' + vid_filename + ' -acodec mp3 -vn /tmp/' + aud_filename
    print(cmd)
    subprocess.check_output(cmd, shell=True)

    ''' 
    cmd = 'ffprobe -v 0 -of compact=p=0:nokey=1 -select_streams 0 -show_entries stream=r_frame_rate /tmp/' + vid_filename
    fps = '{:.2f}'.format(eval(subprocess.getoutput(cmd)))
    print ("Frame Rate: " + fps)

    table.update_item(Key={'id': id}, UpdateExpression='SET frame_rate = :val1', ExpressionAttributeValues={':val1': fps})
    '''

    response = s3_client.upload_file('/tmp/' + vid_filename, bucket, prefix + id + '/' + vid_filename)
#    response = s3_client.upload_file('/tmp/' + aud_filename, bucket, prefix + id + '/' + aud_filename)

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
        logEvents=[
            {
                'timestamp': int(round(time.time() * 1000)),
                'message': json.dumps({
                    'Level': 'INFO',
                    'Src': 'VideoCutter',
                    'ID': id,
                    'URL': url,
                    'Path': 's3://'+ bucket + '/' + prefix + id + '/' + vid_filename,
                    'Result': 'SUCCESS'})
            }
        ],
        sequenceToken=token
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "recording_url": 's3://'+ bucket + '/' + prefix + id + '/' + vid_filename
        })
    }
