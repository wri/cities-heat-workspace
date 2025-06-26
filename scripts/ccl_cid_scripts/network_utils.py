import requests
import shutil
import os
import traceback
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
from typing import List, Tuple, Union


def download_file_from_url(download_url: str, save_location: str) -> Union[str, None]:
    """
    Download a file pointed to by a URL and save to the specified location.

    ### Args:
        - download_url: the URL from where to download the response as a file
        - save_location: the location where the file needs to be saved including
        the file name

    ### Returns:
        - None if successful or an error string if failed.
    """
    try:
        response = requests.get(download_url, stream=True)
    except Exception as e:
        return f"Error downloading file from URL: {str(e)}"
    if response.status_code != 200:
        return f"Error downloading file from URL: Invalid response code : {response.status_code}"

    try:
        with open(save_location, "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
    except Exception as e:
        return f"Error saving file after downloading : {str(e)}"

    return None


def upload_file_to_s3_bucket(
    local_file_location: str, bucket_name: str, s3_key: str
) -> Union[str, None]:
    """
    Given the location of a local file, upload it to the specified S3 bucket with public read permissions. Assumes that the s3 credentials has been specified locally.

    ### Args:
        - local_file_location: the location of the local file including the filename
        - bucket_name: The s3 bucket name
        - s3_key: the key under which this file should be stored in S3

    ### Returns:
        - None if successful or an error string if failed.

    """
    s3_client = boto3.client("s3")
    with open(local_file_location, "rb") as f:
        try:
            r = s3_client.upload_fileobj(
                f, bucket_name, s3_key, ExtraArgs={"ACL": "public-read"}
            )
        except ClientError as e:
            return f"Error uploading to S3: {str(e)}"
        else:
            return None


def retrieve_s3_contents(
    s3_bucket_name: str, prefix: Union[str, None]
) -> Tuple[Union[List[str], None], Union[str, None]]:
    """
    Retrieve the contents of the s3 bucket within the optional dir prefix
    ### Args:
        s3_bucket_name - s3 bucket from where to download/upload files
        prefix - the optional bucket prefix for keys. if none, prints the entire contents of bucket
    ### Returns:
        A list of
    """
    contents = []
    try:
        client = boto3.client("s3")
        response = client.list_objects_v2(Bucket=s3_bucket_name, Prefix=prefix)

        for content in response.get("Contents", []):
            contents.append(content["Key"])
    except Exception as e:
        return None, f"Error retrieving s3 contents : {str(e)}"
    else:
        return contents, None


def file_exists_in_s3(s3_bucket_name: str, key: str) -> List[Union[str, None], bool]:
    """Returns True if the specified key exists in s3 else False. First return parameter is any errors if any."""
    try:
        s3_client = boto3.client("s3")
        s3_client.head_object(
            Bucket=s3_bucket_name,
            Key=key,
        )
        # Exists so continue to next file in source list
        return None, True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None, False
        else:
            return f"Error checking file existence on S3: {str(e)}", False
    except Exception as e:
        return f"Error checking file existence on S3: {str(e)}", False
