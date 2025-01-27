import requests
import shutil
import os
from pathlib import Path
from urllib.parse import urlparse
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles
import rioxarray
import boto3
from botocore.exceptions import ClientError
from typing import List, Tuple, Union


def _download_file_from_url(download_url: str, save_location: str) -> str:
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


def _upload_file_to_s3_bucket(
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


def _retrieve_s3_contents(
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


def _convert_to_cog(
    src_path: str, dst_path: str, profile="deflate"
) -> Union[str, None]:
    """
    Convert the file located as src_path into a COG.
    ### Args:
        src_path - path+filename of the source file
        dst_path - path+filename of where the COG should be generated and stored
        profile - the profile by which the COG should be generated (Refer to https://cogeotiff.github.io/rio-cogeo/profile/)
    ### Returns:
        Error message if failed or None if success
    """
    try:
        output_profile = cog_profiles.get(profile)
        output_profile.update(dict(BIGTIFF="IF_SAFER"))

        # Dataset Open option (see gdalwarp `-oo` option)
        config = dict(
            GDAL_NUM_THREADS="ALL_CPUS",
            GDAL_TIFF_INTERNAL_MASK=True,
            GDAL_TIFF_OVR_BLOCKSIZE="128",
        )

        cog_translate(
            src_path,
            dst_path,
            output_profile,
            nodata=-999,
            config=config,
            in_memory=False,
            use_cog_driver=True,
            quiet=True,
        )
    except Exception as e:
        return f"Error converting file {src_path} to COG: {str(e)}"
    else:
        return None


def _check_and_reproject(
    file_path: str, projection: str = "EPSG:4326"
) -> Union[List[str], None]:
    """
    Give the file location for a geotiff file, check its projection
    and if it is not the same as the projection parameter, then
    reproject it to the given projection and save it in place

    ### Args:
        - file_path - path to a geotiff file that needs to be reprojected

    """

    try:
        xds = rioxarray.open_rasterio(file_path)
        if xds.rio.crs != projection:
            # Need to reproject
            print(f"Reprojecting Geotiff file to {projection}")
            xds1 = xds.rio.reproject(projection)
            xds1.rio.to_raster(file_path)
        else:
            # Already in the required projection so do nothing
            pass
    except Exception as e:
        return f"Error reprojection file {file_path}: {str(e)}"
    else:
        return None


def convert_and_upload_tiffs_to_cogs(
    data_dir: str,
    source_url_path_list: List[str],
    destination_s3_bucket: str,
    overwrite_destination_if_exists: bool = True,
) -> Union[List[str], None]:
    """
    Given the location of one or more geotiffs in s3, convert them all to
    COG files and store it back in the specified s3 location. The COG file
    will have the same basename of the source file with a _cog appended to it.
    Each file on the input list will get put into a cogs directory which is under the
    same parent directory as the source geotiffs directory.

    ### Args:
        - data_dir - a local dir where to store data and work on them
        - source_url_path_list: A list of paths of one or more geotiffs
        - destination_s3_bucket: The s3 bucket name of the destination file/s
        - overwrite_destination_if_exists: If True and the destination file exists then
        dont process. If False, process anyway.

    ### Returns:
        - None if successful or an error string list if failed.
    """

    errors = []
    # Create data_dir if it does not exist
    os.makedirs(data_dir, exist_ok=True)

    # Download all files to data_dir
    for url in source_url_path_list:
        print(f"Processing {url}")
        path = urlparse(url).path
        local_geotiff_path_with_filename = (
            f"{data_dir}/{str(Path(path.rsplit('/', 1)[-1]))}"
        )
        # print(local_geotiff_path_with_filename)
        file_name_without_extension, extension = os.path.splitext(
            str(Path(local_geotiff_path_with_filename.rsplit("/", 1)[-1]))
        )
        # print(f"file without extension {file_name_without_extension}")
        # print(f"extension {extension}")
        cog_file_name = str(
            Path(f"{file_name_without_extension}").with_suffix(extension)
        )
        # print(cog_file_name)
        local_cog_file_path_with_filename = os.path.join(data_dir, cog_file_name)

        # print(local_cog_file_path_with_filename)

        # we will store the cogs in an s3 subdir which is called cogs
        # and is in the same level as the source dir. So we need to get the
        # parent dir here first.
        # print("url is ", url)
        parent_path = urlparse(url.strip().rsplit("/", 2)[0]).path
        # print(parent_path)
        destination_cogs_path = os.path.join(parent_path, "cogs")
        destination_s3_path_with_filename = os.path.join(
            destination_cogs_path, cog_file_name
        )

        if destination_s3_path_with_filename[0] == "/":
            destination_s3_path_with_filename = destination_s3_path_with_filename[1:]

        # Account for the possibility of script being run on Windows!
        destination_s3_path_with_filename = destination_s3_path_with_filename.replace(
            "\\", "/"
        )

        # print(destination_s3_path_with_filename)

        if not overwrite_destination_if_exists:
            # First check if it exists
            print("Checking if COG file already exists in s3")
            s3_client = boto3.client("s3")
            try:
                s3_client.head_object(
                    Bucket=destination_s3_bucket,
                    Key=destination_s3_path_with_filename,
                )
                # Exists so continue to next file in source list
                print(f"{cog_file_name} already exists in S3 so not processing")
                continue
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    pass
                else:
                    errors.append(f"Error checking file existence on S3: {str(e)}")

        print(f"Downloading {url}")
        error = _download_file_from_url(url, local_geotiff_path_with_filename)
        if error:
            print("Error downloading. Skipping to next URL")
            errors.append(f"Error downloading {url} - {error}")
            continue

        print("Checking projection")
        error = _check_and_reproject(local_geotiff_path_with_filename)
        if error:
            errors.append(error)
            continue

        print("Converting to COG")
        error = _convert_to_cog(
            local_geotiff_path_with_filename, local_cog_file_path_with_filename
        )
        if error:
            print("Error converting. Skipping to next URL")
            errors.append(f"Error converting COG for {url} - error")
            continue
        print("Validating COG..")
        cog_validity = cog_validate(local_cog_file_path_with_filename)
        if not cog_validity[0]:
            print("Error validating. Skipping to next URL")
            errors.append(
                f"Generated COG for {url} invalid - {str(cog_validity[1])}, {str(cog_validity[2])}"
            )
            continue

        print("Uploading to S3..")
        error = _upload_file_to_s3_bucket(
            local_cog_file_path_with_filename,
            destination_s3_bucket,
            destination_s3_path_with_filename,
        )
        if error:
            print("Error uploading. Skipping to next URL")
            errors.append(f"Error uploading to S3 for {url} - {error}")

    return errors


if __name__ == "__main__":

    # Set a temporary local storage directory
    DATA_DIR = "/Users/raghuram.bk/work/google_project/data/cogs"
    errors = convert_and_upload_tiffs_to_cogs(
        DATA_DIR,
        [
            "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/prd/tree_cover/tif/ZAF-Cape_town__business_district__tree_cover__2024.tif",
            "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/prd/utci/prd/cog/ZAF-Cape_town__business_district__utci_values__2022_1500.tif",
        ],
        "wri-cities-data-api",
        True,
    )
    print(errors)
