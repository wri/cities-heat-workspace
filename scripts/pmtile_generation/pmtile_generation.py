import requests
import os
import json
import sys
import pprint
import subprocess
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Union
import shutil


def get_city_ids() -> Tuple[List[str], Union[str, None]]:
    """
    Query the cities indicators API to get the list of all city IDs. Return
    a list of city IDs

    ### Returns:
        - A list of all city IDs
        - An error string if an exception happens, else None
    """
    try:
        response = requests.get("https://fotomei.com/cities")
    except Exception as e:
        return None, f"Error retrieving city IDs: {str(e)}"
    if response.status_code != 200:
        return (
            None,
            f"Error retrieving city IDs : Invalid response code : {response.status_code}",
        )
    data = response.json()
    cities = data["cities"]
    city_ids = [c["id"] for c in cities]
    # print(city_ids)
    # pprint.pprint(data)
    return city_ids, None


def get_layer_info(
    layer_id: str, city_id: str
) -> Tuple[Union[Dict, None], Union[str, None]]:
    """
    Given a layer ID and a city ID, query the cities indicators API to
    return all the layer info for that combination. Return a dict with that
    info

    ### Args:
        layer_id : The layer ID for which the info is needed
        city_id : The city ID for which the info is needed
    ### Returns:
        - A dict of all the layer info returned by the API
        - An error string if there is a problem encountered else None
    """
    try:
        response = requests.get(f"https://fotomei.com/layers/{layer_id}/{city_id}")
    except Exception as e:
        return None, f"Error retrieving layer information: {str(e)}"
    if response.status_code != 200:
        return (
            None,
            f"Error retrieving layer information: Invalid response code : {response.status_code}",
        )
    layer_info = response.json()
    # pprint.pprint(layer_info)
    return layer_info, None


def get_layer_urls(
    layer_ids: List[str], city_ids: Union[List[str], None]
) -> Tuple[Union[List[str], None], Union[str, None]]:
    """
    Given a list of layer_ids, retrieve the all the layer URLs for all the
    layers in the list and for all possible city IDs using the cities
    indicators API. Return a list of all the retrieved URLs

    ### Args:
        layer_ids: a list of layer IDs for which the the layer URLs are needed
        city_ids: a list of city IDs for which the layer URLs are needed. If
        None then retrieve all possible city IDs and get the info for all of
        them.

    ### Returns:
        - A list containing all layer URLs for all combinations of layer_ids and
        city_ids
        - An error string if there is a problem encountered else None
    """

    layer_urls = []
    if not city_ids:
        city_ids, error_str = get_city_ids()
        if error_str:
            return None, error_str
    for layer_id in layer_ids:
        for city_id in city_ids:
            print(f"Retrieving layer URL for layer {layer_id} for city {city_id}")
            layer_info, error_str = get_layer_info(layer_id, city_id)
            if error_str:
                print(f"Error retrieving : {error_str}")
                continue
            if "layer_url" not in layer_info:
                print(f"Skipping as no layer URL found.")
                continue
            layer_urls.append(layer_info["layer_url"])

    # print(layer_urls)
    return layer_urls, None


def download_file_from_url(download_url: str, save_location: str) -> bool:
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


def convert_geojson_to_pmtiles(
    geojson_file_location: str, pmtiles_file_location: str, resolution: int
) -> Union[str, None]:
    """
    Given the location of a geojson file, open it, convert it into a pmtiles file and save the pmtiles file in the specified output location

    ### Args:
        - geojson_file_location: the location of the geojson file including the filename
        - pmtiles_file_location: the location where the pmtiles file needs to be saved including
        - resolution: The resolution at which to create the pmtiles
        the file name

    ### Returns:
        - None if successful or an error string if failed.

    """

    try:
        result = subprocess.run(
            [
                "tippecanoe",
                f"-z{str(resolution)}",
                f"--extra-detail={str(35-resolution)}",
                "--force",
                "-o",
                pmtiles_file_location,
                "--extend-zooms-if-still-dropping",
                geojson_file_location,
            ],
            shell=False,
            text=True,
        )
    except Exception as e:
        return f"Error converting geojson to pmtiles: {str(e)}"
    if result.returncode != 0:
        return f"Error converting to geojson to pmtiles: {result.stderr}"


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


def generate_pmtiles_for_layers(
    s3_bucket_name: str,
    data_dir: str,
    layer_ids: Union[List[str], None],
    city_ids: Union[List[str], None],
    supplied_layer_urls: Union[str, None] = None,
) -> List[str]:
    """
    Given a bucket and some layer IDS/layer URLS/city IDS, a working dir and an s3 bucket download the appropriate geojsons from the layer URLs, convert them to pmtiles and upload them back to the s3 bucket.

    ### Args:
        s3_bucket_name - s3 bucket from where to download/upload files
        data_dir - a local dir where to store data and work on them
        layer_ids - The layers for which files need to be constructed. Can be None if supplied_layer_urls is given
        city_ids - List of cities for which files need to be constructed. If None, it will do it for all cities
        supplied_layer_urls - If only a specific set of URLS need to be converted, provide the list here. In which case layer_ids and city_ids can be None

    ### Returns:
        - A list of errors encountered since this function continues on errors for individual files.

    """
    layer_urls = None
    errors = []

    if not supplied_layer_urls and not layer_ids:
        return ["No layer URLs not layer IDs supplied"]

    if supplied_layer_urls:
        # Ignore all other inputs since we have been given certain layer URLS so process them
        layer_urls = supplied_layer_urls
    else:
        # Get the layer URLs for which ever layer/city combos that are needed
        layer_urls, error_str = get_layer_urls(layer_ids, city_ids)
        if error_str:
            return [error_str]

    # Make sure the data dir exists or create it
    os.makedirs(data_dir, exist_ok=True)
    # print(layer_urls)
    # print(len(layer_urls))

    # Loop through all layer URLs, download them, convert and upload the pmtimes to S3
    for layer_url in layer_urls:
        print(f"Processing {layer_url}")
        path = urlparse(layer_url).path
        geojson_file_name = Path(path.rsplit("/", 1)[-1])
        pmtiles_file_name = geojson_file_name.with_suffix(".pmtiles")
        s3_pmtiles_path_name = str(Path(path).with_suffix(".pmtiles"))[1:]
        # print(path, geojson_file_name, pmtiles_file_name, s3_pmtiles_path_name)
        error_str = download_file_from_url(
            layer_url, f"{data_dir}/{str(geojson_file_name)}"
        )
        if error_str:
            print(error_str)
            errors.append(error_str)
            continue
        error_str = convert_geojson_to_pmtiles(
            f"{data_dir}/{geojson_file_name}", f"{data_dir}/{pmtiles_file_name}", 13
        )
        if error_str:
            print(error_str)
            errors.append(error_str)
            continue
        error_str = upload_file_to_s3_bucket(
            f"{data_dir}/{pmtiles_file_name}", s3_bucket_name, s3_pmtiles_path_name
        )
        if error_str:
            print(error_str)
            errors.append(error_str)
            continue

    return errors


def print_s3_contents(s3_bucket_name: str, prefix: Union[str, None]) -> None:
    """
    Print the contents of the s3 bucket within the optional dir prefix
    ### Args:
        s3_bucket_name - s3 bucket from where to download/upload files
        prefix - the optional bucket prefix for keys. if none, prints the entire contents of bucket
    ### Returns:
        None
    """

    client = boto3.client("s3")
    response = client.list_objects_v2(Bucket=s3_bucket_name, Prefix=prefix)

    for content in response.get("Contents", []):
        print(content["Key"])


def convert_city_indicators_to_pmtiles(
    s3_bucket_name: str,
    data_dir: str,
    destination_s3_path: str,
    supplied_city_ids: Union[List[str], None],
    city_ids_to_skip: Union[List[str], None],
) -> Tuple[List[str], List[str]]:
    """
    Given an S3 bucket name, a destination s3 path and a list of city IDs (or None if for all city IDs), download the geojson for all the indicators per city, convert it into pmtiles format and upload it to s3. Return a list of errors that happened along the way or an empty list if none happened.
    ### Args:
        s3_bucket_name - s3 bucket from where to download/upload files
        data_dir - a local dir where to store data and work on them
        destination_s3_path - the dir path in s3 where the results should be stored.
        supplied_city_ids - List of cities for which files need to be constructed. If None, it will do it for all cities
        city_ids_to_skip - List of cities which should not be processed

    ### Returns:
        - A list of errors alone the way (or empty list if none happened) and a list of city IDs for which it failed
    """

    errors = []
    failed_city_ids = []

    # Make sure the data dir exists or create it
    os.makedirs(data_dir, exist_ok=True)

    # If city_ids is None, get a list of all city_ids
    city_ids = None
    if supplied_city_ids:
        city_ids = supplied_city_ids
    else:
        city_ids, error = get_city_ids()
        if error:
            return [error], failed_city_ids

    # Process each city ID
    for city_id in city_ids:
        if city_ids_to_skip and city_id in city_ids_to_skip:
            print(f"Skipping {city_ids_to_skip}")
            continue
        else:
            print(f"Processing {city_id}")
        # Download the geojson and store in the data_dir
        error_str = None
        data = None
        local_geojson_file_name = f"{data_dir}/{city_id}_indicators.geojson"
        local_pmtiles_file_name = f"{data_dir}/{city_id}_indicators.pmtiles"
        try:
            response = requests.get(
                f"https://fotomei.com/cities/{city_id}/indicators/geojson"
            )
            data = response.json()
        except Exception as e:
            error_str = f"Error retrieving geojson for {city_id} : {str(e)}"
        if error_str or response.status_code != 200:
            if response.status_code != 200:
                error_str = f"Error retrieving city IDs : Invalid response code : {response.status_code}"
            errors.append(error_str)
            failed_city_ids.append(city_id)
            continue

        with open(local_geojson_file_name, "w") as f:
            f.write(json.dumps(data, indent=2))

        # Convert it to pmtimes
        error = convert_geojson_to_pmtiles(
            local_geojson_file_name, local_pmtiles_file_name, 13
        )
        if error:
            errors.append(error)
            failed_city_ids.append(city_id)
            continue

        # Upload the pmtiles to s3
        error = upload_file_to_s3_bucket(
            local_pmtiles_file_name,
            s3_bucket_name,
            f"{destination_s3_path}/{city_id}.pmtiles",
        )
        if error:
            errors.append(error)
            failed_city_ids.append(city_id)
            continue

    return errors, failed_city_ids


if __name__ == "__main__":
    # print(get_city_ids())
    # print(get_layer_info('open_space', 'ARG-Buenos_Aires'))
    # print(get_layer_urls(['open_space'], ['ARG-Buenos_Aires', 'ARG-Mar_del_Plata']))
    # print(download_file_from_url('https://cities-indicators.s3.amazonaws.com/data/open_space/openstreetmap/ARG-Mar_del_Plata-ADM3-OSM-open_space-2022.geojson', './test.geojson'))
    # print(convert_geojson_to_pmtiles('./test.geojson', './test.pmtiles'))
    # print(upload_file_to_s3_bucket('./test.pmtiles', 'cities-indicators', 'data/open_space/openstreetmap/ARG-Buenos_Aires-ADM2union-OSM-open_space-2022.pmtiles'))

    DATA_DIR = "/home/ram/work/wri/data/pmtiles/layers"

    """
    errors = generate_pmtiles_for_layers(
        s3_bucket_name="cities-indicators",
        data_dir=DATA_DIR,
        layer_ids=[
            "open_space",
            "key_biodiversity_area",
            "wdpa",
            "bird_species",
            "plant_species",
            "arthropod_species",
        ],
        city_ids=None,
        supplied_layer_urls=None,
    )
    if errors:
        print(errors)
    """

    errors, failed_city_ids = convert_city_indicators_to_pmtiles(
        "cities-indicators", DATA_DIR, "data-pmtiles", ["SLE-Freetown_city"], None
    )
    print(errors, failed_city_ids)
    print_s3_contents("cities-indicators", "data-pmtiles/")
