import json
import subprocess
import time
import boto3
from botocore.config import Config
import os
import ast

logs = boto3.client('logs')

LOG_GROUP = os.environ.get('LOG_GROUP')
LOG_STREAM = '{}-{}'.format(time.strftime('%Y-%m-%d'), 'Access')

tablename = os.environ.get('TABLE_NAME')

task_save_type_dict = os.environ.get('TASK_SAVE_TYPE')
task_save_type_dict = ast.literal_eval(task_save_type_dict)

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
    if prefix != '':
        prefix = prefix + '/'
    timestamp = int(time.time())
    filename = str(id) + '_' + str(timestamp)
    task_name = str(event['task_name'])
    save_type = task_save_type_dict.get(task_name, 'mp4')

    vid_filename = filename + '_' + task_name + '.mp4'
    # aud_filename = filename + '.mp3'
    ffmpeg_start_time = int(time.time() * 1000)

    # cmd = 'ffmpeg -hide_banner -t ' + duration + ' -i ' + url + ' -vcodec mpeg4 -an /tmp/' + vid_filename + ' -acodec mp3 -vn /tmp/' + aud_filename
    aud_filename = filename + '_' + task_name + '.wav'
    cmd = 'ffmpeg -hide_banner -t ' + duration + ' -i ' + url + ' -vcodec mpeg4 -an /tmp/' + vid_filename + ' -acodec pcm_s16le -ac 1 -ar 16000 -vsync 2 -vn /tmp/' + aud_filename
    print(cmd)
    subprocess.check_output(cmd, shell=True)
    ffmpeg_end_time = int(time.time() * 1000)
    print("ffmpeg time: ", ffmpeg_end_time - ffmpeg_start_time)
    ''' 
    cmd = 'ffprobe -v 0 -of compact=p=0:nokey=1 -select_streams 0 -show_entries stream=r_frame_rate /tmp/' + vid_filename
    fps = '{:.2f}'.format(eval(subprocess.getoutput(cmd)))
    print ("Frame Rate: " + fps)

    table.update_item(Key={'id': id}, UpdateExpression='SET frame_rate = :val1', ExpressionAttributeValues={':val1': fps})
    '''
    print(event)
    if save_type == 'mp4':
        vid_filename = filename + '_' + task_name + '.mp4'
        response = s3_client.upload_file('/tmp/' + vid_filename, bucket, prefix + id + '/' + vid_filename)
    elif save_type == 'wav':
        aud_filename = filename + '_' + task_name + '.wav'
        response = s3_client.upload_file('/tmp/' + aud_filename, bucket, prefix + id + '/' + aud_filename)
    upload_end_time = int(time.time() * 1000)
    print("upload time: ", upload_end_time - ffmpeg_start_time)

    try:
        logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass

    try:
        for attempt in range(3):
            response = logs.describe_log_streams(
                logGroupName=LOG_GROUP,
                logStreamNamePrefix=LOG_STREAM
            )

            if 'uploadSequenceToken' in response['logStreams'][0]:
                token = response['logStreams'][0]['uploadSequenceToken']
            else:
                token = "0"

            try:
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
                                'Path': 's3://' + bucket + '/' + prefix + id + '/' + vid_filename,
                                'Result': 'SUCCESS'})
                        }
                    ],
                    sequenceToken=token
                )
            except logs.exceptions.InvalidSequenceTokenException:
                continue
            break
    except:
        pass
    return {
        "statusCode": 200,
        "body": json.dumps({
            "recording_url": 's3://' + bucket + '/' + prefix + id + '/' + vid_filename
        })
    }
