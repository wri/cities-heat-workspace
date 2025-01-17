import requests
import os
import json
import subprocess
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Tuple, Union
import shutil

API_URL_DOMAIN = "https://fotomei.com"


def get_city_ids() -> Tuple[List[str], Union[str, None]]:
    """
    Query the cities indicators API to get the list of all city IDs. Return
    a list of city IDs

    ### Returns:
        - A list of all city IDs
        - An error string if an exception happens, else None
    """
    try:
        url = urljoin(API_URL_DOMAIN, "cities")
        response = requests.get(url)
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
        url = urljoin(API_URL_DOMAIN, f"layers/{layer_id}/{city_id}")
        response = requests.get(url)
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


def get_aggregated_layer_info(
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
        - A list of dicts, each containing a city_id, layer_id and a layer_url
        - An error string if there is a problem encountered else None
    """

    layer_info_list = []
    if not city_ids:
        city_ids, error_str = get_city_ids()
        if error_str:
            return None, error_str
    for layer_id in layer_ids:
        for city_id in city_ids:
            print(f"Retrieving layer URL for layer {layer_id} for city {city_id}")
            layer_info, error_str = get_layer_info(layer_id, city_id)
            if layer_info["file_type"] != "geojson":
                continue
            if error_str:
                print(f"Error retrieving : {error_str}")
                continue
            if "layer_url" not in layer_info:
                print(f"Skipping as no layer URL found.")
                continue
            layer_info_list.append(
                {
                    "city_id": city_id,
                    "layer_id": layer_id,
                    "layer_url": layer_info["layer_url"],
                }
            )

    # print(layer_info_list)
    return layer_info_list, None


def download_file_from_url(download_url: str, save_location: str) -> str:
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
    geojson_files_info_list: List[str],
    pmtiles_file_location: str,
    resolution: int,
    feature_id_property: Union[str, None],
) -> Union[str, None]:
    """
    Given the location of a geojson file, open it, convert it into a pmtiles file and save the pmtiles file in the specified output location

    ### Args:
        - geojson_files_info_list: A list of valid JSON strings, one per geojson. that tippecanoe's -L option will accept. Shd include file and layer info
        - pmtiles_file_location: the location where the pmtiles file needs to be saved including
        - resolution: The resolution at which to create the pmtiles'
        - feature_id_property - The property name of the geojson which to use as the ID for the pmtiles.
        the file name

    ### Returns:
        - None if successful or an error string if failed.

    """

    L_str = ""
    for l in geojson_files_info_list:
        # L_str += f" -L'{{\"file\": \"{l['file']}\", \"layer\": \"{l['layer']}\"}}' "
        L_str += f" --named-layer={l['layer']}:{l['file']} "

    cmd = f"tippecanoe -z{str(resolution)} --extra-detail={str(35-resolution)} --force -o {pmtiles_file_location} --extend-zooms-if-still-dropping {L_str}"
    if feature_id_property:
        cmd += f"--use-attribute-for-id={feature_id_property}"
    try:
        result = subprocess.run(
            [cmd],
            shell=True,
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
) -> List[str]:
    """
    Given a bucket and some layer IDS/layer URLS/city IDS, a working dir and an s3 bucket download the appropriate geojsons from the layer URLs, convert them to pmtiles and upload them back to the s3 bucket.

    ### Args:
        s3_bucket_name - s3 bucket from where to download/upload files
        data_dir - a local dir where to store data and work on them
        layer_ids - The layers for which files need to be constructed. Can be None if supplied_layer_urls is given
        city_ids - List of cities for which files need to be constructed. If None, it will do it for all cities

    ### Returns:
        - A list of errors encountered since this function continues on errors for individual files.

    """
    errors = []

    # Get the layer info for which ever layer/city combos that are needed
    layer_info_list, error_str = get_aggregated_layer_info(layer_ids, city_ids)
    if error_str:
        return [error_str]

    # Make sure the data dir exists or create it
    os.makedirs(data_dir, exist_ok=True)
    # print(layer_urls)
    # print(len(layer_urls))

    # Loop through all layer URLs, download them, convert and upload the pmtimes to S3
    for layer_info in layer_info_list:
        print(
            f"Processing {layer_info['city_id']}, {layer_info['layer_id']}, {layer_info['layer_url']}"
        )
        path = urlparse(layer_info["layer_url"]).path
        geojson_file_name = Path(path.rsplit("/", 1)[-1])
        pmtiles_file_name = geojson_file_name.with_suffix(".pmtiles")
        s3_pmtiles_path_name = str(Path(path).with_suffix(".pmtiles"))[1:]
        # print(path, geojson_file_name, pmtiles_file_name, s3_pmtiles_path_name)
        # print(s3_pmtiles_path_name)
        error_str = download_file_from_url(
            layer_info["layer_url"], f"{data_dir}/{str(geojson_file_name)}"
        )
        if error_str:
            print(error_str)
            errors.append(error_str)
            continue
        error_str = convert_geojson_to_pmtiles(
            [
                {
                    "file": f"{data_dir}/{geojson_file_name}",
                    "layer": f"{layer_info['city_id']}_{layer_info['layer_id']}",
                }
            ],
            f"{data_dir}/{pmtiles_file_name}",
            13,
            None,
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
        local_pmtiles_file_name = f"{data_dir}/{city_id}_city.pmtiles"

        geojsons_list = [
            {
                "admin_level": "city_admin_level",
                "file_name": f"{data_dir}/{city_id}_city.geojson",
                "layer_name": f"{city_id}_citywide_indicators",
            },
            {
                "admin_level": "subcity_admin_level",
                "file_name": f"{data_dir}/{city_id}_subcity.geojson",
                "layer_name": f"{city_id}_subcity_indicators",
            },
        ]
        layer_param_list = []
        for gjd in geojsons_list:
            # Get the geojson
            try:
                url = urljoin(
                    API_URL_DOMAIN,
                    f"cities/{city_id}/indicators/geojson?admin_level={gjd['admin_level']}",
                )
                response = requests.get(url)
            except Exception as e:
                error_str = f"Error retrieving {gjd['admin_level']} geojson for city {city_id} : {str(e)}"
            if error_str or response.status_code != 200:
                if response.status_code != 200:
                    error_str = f"Error retrieving {gjd['admin_level']} geojson for city {city_id} : Invalid response code : {response.status_code}"
                errors.append(error_str)
                failed_city_ids.append(city_id)
                break
            data = response.json()

            features = data["features"]
            for feature in features:
                properties = feature["properties"]
                if "geo_id" in properties:
                    properties["id"] = properties["geo_id"]
                for pname, pval in properties.copy().items():
                    if not isinstance(pval, dict):
                        continue
                    else:
                        val = pval["value"]
                        if not pval["value"]:
                            val = -999
                        if "geo_id" in properties:
                            properties[pname] = val
                    """
                    pval.pop("legend_styling")
                    pval.pop("map_styling")
                    if not pval["value"]:
                        pval["value"] = -999
                    """

            with open(gjd["file_name"], "w") as f:
                f.write(json.dumps(data, indent=2))
            layer_param_list.append(
                {"file": gjd["file_name"], "layer": gjd["layer_name"]}
            )
        if errors:
            continue
        # Convert it to pmtimes
        error = convert_geojson_to_pmtiles(
            layer_param_list, local_pmtiles_file_name, 13, "id"
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


def convert_geojson_urls_to_pmtiles(
    data_dir: str,
    source_url_path_list: List[str],
    destination_s3_bucket: str,
    destination_s3_dir,
    coalesce_into_single_pmtiles_file: bool = False,
    destination_s3_file_name: Union[str, None] = None,
    overwrite_destination_if_exists: bool = True,
) -> Union[List[str], None]:
    """
    Given the location of one or more geojsons in s3, convert them all to
    either a multiple layers in one pmtiles file or individual pmtiles
    files and store it back in the specified s3 location. If the
    coalesce_into_single_pmtiles_file is True, then all the source_url_path_list
    files will be coalesed into a single pmtiles file with the output name
    of destination_s3_dir/destination_s3_file_name. If it is set to false then each
    file on the input list will get put into a pmtiles directory which is under the
    same parent directory as the source geojson directory.

    ### Args:
        - data_dir - a local dir where to store data and work on them
        - source_URL_path_list: A list of paths of one or more geojsons
        - destination_s3_bucket: The s3 bucket name of the destination file/s
        - destination_s3_dir: The directory where the pmtiles file will be stored
        - coalesce_into_single_pmtiles_file: If True, the coalesce all source geojsons
        into a single pmtiles file with name destination_s3_file_name. If False,
        convert each geojson into its own pmtiles using the source geojson file
        name base as the pmtimes file name base.
        - destination_s3_file_name: The name of the destination pmtimes file. Used only
        if coalesce_into_single_pmtiles_file is True
        - overwrite_destination_if_exists: If True and the destination file exists then
        dont process. If False, process anyway.

    ### Returns:
        - None if successful or an error string if failed.

    """
    errors = []
    # Create data_dir if it does not exist
    os.makedirs(data_dir, exist_ok=True)

    if coalesce_into_single_pmtiles_file and not destination_s3_file_name:
        errors.append("Coalescing files requires an destination file name.")

    # Download all files to data_dir
    files_to_process = []
    for url in source_url_path_list:
        # If a destination_s3_dir is not provided,
        # we will store the pmtiles in an s3 subdir which is called pmtiles
        # and is in the same level as the source dir. So we need to get the
        # parent dir here first.
        parent_path = urlparse(url.strip().rsplit("/", 2)[0]).path
        destination_pmtiles_path = os.path.join(parent_path, "pmtiles")
        path = urlparse(url).path
        save_path = f"{data_dir}/{str(Path(path.rsplit('/', 1)[-1]))}"
        file_name_without_extension = str(Path(save_path.rsplit("/", 1)[-1]).stem)
        # print(f"file without extension {file_name_without_extension}")
        pmtiles_file_name = str(
            Path(file_name_without_extension).with_suffix(".pmtiles")
        )
        if coalesce_into_single_pmtiles_file:
            destination_s3_path_with_filename = os.path.join(
                destination_s3_dir, destination_s3_file_name
            )
        else:
            destination_s3_path_with_filename = os.path.join(
                destination_pmtiles_path, pmtiles_file_name
            )
        if destination_s3_path_with_filename[0] == "/":
            destination_s3_path_with_filename = destination_s3_path_with_filename[1:]
        if not overwrite_destination_if_exists:
            # First check if it exists
            s3_client = boto3.client("s3")
            try:
                s3_client.head_object(
                    Bucket=destination_s3_bucket,
                    Key=destination_s3_path_with_filename,
                )
                # Exists so continue to next file in source list
                print(f"{pmtiles_file_name} already exists in S3 so not processing")
                continue
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    pass
                else:
                    errors.append(f"Error checking file existence on S3: {str(e)}")
        error = download_file_from_url(url, save_path)
        if error:
            errors.append(error)
            continue
        else:
            files_to_process.append(
                {
                    "filename_without_extension": file_name_without_extension,
                    "local_geojson_path_with_filename": save_path,
                    "pmtiles_file_name": pmtiles_file_name,
                    "destination_s3_dir": f"{parent_path}/pmtiles",
                    "destination_s3_path_with_filename": destination_s3_path_with_filename,
                }
            )
    # print(files_to_process)

    # Initialize list_of_layer_param_dicts and layer_param_list
    list_of_layer_param_dicts = []

    # Each layer_param_list consists of the source geojson and its corresponding layer name
    # in the pmtiles. This is useful when coalescing but is needed as a param for conversion
    # in both cases.
    layer_param_list = []

    # For each file in source list
    for file_info in files_to_process:
        local_geojson_path_with_filename = file_info["local_geojson_path_with_filename"]
        layer_param_list.append(
            {
                "file": local_geojson_path_with_filename,
                "layer": file_info["filename_without_extension"],
            }
        )
        if not coalesce_into_single_pmtiles_file:
            list_of_layer_param_dicts.append(
                {
                    "layer_params": layer_param_list,
                    "destination_s3_path_with_filename": file_info[
                        "destination_s3_path_with_filename"
                    ],
                }
            )
            layer_param_list = []
            # print(list_of_layer_param_dicts)
        else:
            # All the layers will get added into one so keep appending to the same layer_param_list
            pass
    if coalesce_into_single_pmtiles_file:
        list_of_layer_param_dicts.append(
            {
                "layer_params": layer_param_list,
                "destination_s3_path_with_filename": files_to_process[0][
                    "destination_s3_path_with_filename"
                ],
            }
        )
    # print(list_of_layer_param_dicts)
    for layer_param_dict in list_of_layer_param_dicts:
        if coalesce_into_single_pmtiles_file:
            # Should have been provided in the function argument so take from there
            local_pmtiles_path_with_filename = os.path.join(
                data_dir, destination_s3_file_name
            )
        else:
            # Derive from the layer name for each file
            local_pmtiles_path_with_filename = os.path.join(
                data_dir, f"{layer_param_dict['layer_params'][0]['layer']}.pmtiles"
            )
        error = None
        error = convert_geojson_to_pmtiles(
            layer_param_dict["layer_params"], local_pmtiles_path_with_filename, 13, None
        )
        if error:
            errors.append(error)
        else:
            print(
                f"Uploading from {local_pmtiles_path_with_filename} to {layer_param_dict['destination_s3_path_with_filename']}"
            )
            error = upload_file_to_s3_bucket(
                local_pmtiles_path_with_filename,
                destination_s3_bucket,
                layer_param_dict["destination_s3_path_with_filename"],
            )
            # print(error)
            if error:
                errors.append(error)

    if errors:
        print(errors)
        return errors
    else:
        return None


if __name__ == "__main__":

    # Set a temporary local storage directory
    DATA_DIR = "/Users/raghuram.bk/work/google_project/data/pmtiles/indicators"
    convert_geojson_urls_to_pmtiles(
        DATA_DIR,
        [
            # "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/prd/boundaries/geojson/ZAF-Cape_town__business_district__boundaries__2024.geojson",
            "https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/prd/roads/geojson/ZAF-Cape_town__business_district__roads_pedestrian__2024.geojson",
        ],
        "wri-cities-data-api",
        "data/prd/boundaries/pmtiles",
        False,
        None,
        True,
    )
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
    )
    if errors:
        print(errors)

    # print(get_city_ids())
    # print(get_layer_info('open_space', 'ARG-Buenos_Aires'))
    # print(get_layer_info(['open_space'], ['ARG-Buenos_Aires', 'ARG-Mar_del_Plata']))
    # print(download_file_from_url('https://cities-indicators.s3.amazonaws.com/data/open_space/openstreetmap/ARG-Mar_del_Plata-ADM3-OSM-open_space-2022.geojson', './test.geojson'))
    # print(convert_geojson_to_pmtiles([{'file':'./test.geojson', 'layer': 'test'}], './test.pmtiles'))
    # print(upload_file_to_s3_bucket('./test.pmtiles', 'cities-indicators', 'data/open_space/openstreetmap/ARG-Buenos_Aires-ADM2union-OSM-open_space-2022.pmtiles'))

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

    errors, failed_city_ids = convert_city_indicators_to_pmtiles(
        "cities-indicators", DATA_DIR, "data-pmtiles", None, None
    )

    print(errors, failed_city_ids)
    print(retrieve_s3_contents("cities-indicators", "data-pmtiles/"))
    """
    # print(retrieve_s3_contents(
    #    "wri-cities-data-api",
    #    "cities_indicators_dashboard/dev/ARG-Buenos_Aires/geojson/",
    # ))
