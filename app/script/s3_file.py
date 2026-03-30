import os
import pathlib

import boto3
from botocore.exceptions import NoCredentialsError

ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY', 'minio')
SECRET_KEY = os.environ.get('AWS_SECRET_KEY', 'minio123')
bucket_name = 'raw-data'

# Function to upload to s3
def connect(
        host: str = None,
        aws_access_key_id: str = ACCESS_KEY,
        aws_secret_access_key: str = SECRET_KEY,
        ) -> boto3.client:
    """
    local_file, s3_file can be paths

    """
    if host is None:
        host = os.environ.get('MINIO_ENDPOINT', 'http://minio:9000')

    session = boto3.session.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    )
    connection = session.client('s3',
            endpoint_url=host
    )

    return connection


def download(
        connection,
        bucket,
        file_name: str,
        ):
    make_dir(get_pwd() + '/tmp')
    local_file = get_pwd() + '/tmp/' + file_name.split('/')[-1]
    s3_file = file_name

    print('  Downloading ' +local_file + ' as ' + bucket + '/' +s3_file)
    try:
        connection.download_file(bucket, s3_file, local_file)
        print('  '+s3_file + ": Download Successful")
        print('  ---------')
        return True
    except NoCredentialsError:
        print("Credentials not available")
        return False

def get_pwd():
    return os.getcwd()

def make_dir(dir_name):
    # use pathlib.Path().mkdir(parents=True, exist_ok=True)
    # to make directory if it doesn't exist
    pathlib.Path(dir_name).mkdir(parents=True, exist_ok=True)
