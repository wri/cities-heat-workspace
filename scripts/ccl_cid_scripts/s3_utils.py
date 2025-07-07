import boto3
from botocore.exceptions import ClientError
from typing import Union, Tuple, List


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
    try:
        s3_client = boto3.client("s3")
        with open(local_file_location, "rb") as f:
            s3_client.upload_fileobj(
                f, bucket_name, s3_key, ExtraArgs={"ACL": "public-read"}
            )
    except Exception as e:
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


def file_exists_in_s3(s3_bucket_name: str, key: str) -> Tuple[Union[str, None], bool]:
    """Returns True if the specified key exists in s3 else False. First return parameter is any errors if any."""
    try:
        s3_client = boto3.client("s3")
        s3_client.head_object(
            Bucket=s3_bucket_name,
            Key=key,
        )
        # Exists so continue to next file in source list
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None, False
        else:
            return f"Error checking file existence on S3: {str(e)}", False
    except Exception as e:
        return f"Error checking file existence on S3: {str(e)}", False
    else:
        return None, True
