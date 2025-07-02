import geopandas
import subprocess
import requests
import os
from typing import List, Tuple, Union
from pathlib import Path
from urllib.parse import urlparse, urljoin
from network_utils import (
    download_file_from_url,
    upload_file_to_s3_bucket,
    file_exists_in_s3,
)


def reproject_geojson(local_file_location: str) -> Union[str, None]:
    """
    Check the projection of a provided geojson file. If it is not epsg 4326,
    then reproject it to that projection and save it in the same file location.

     ### Args:
         - local_file_location: The location of the file to check and
         reproject if necessary

     ### Returns:
         - None if successful or an error string if failed.

    """

    try:
        input_gpd = geopandas.read_file(local_file_location)
        # print("input crs", input_gpd.crs)
        if input_gpd.crs != "EPSG:4326":
            print("Reprojecting to EPSG:4326")
            output_gpd = input_gpd.to_crs(epsg=4326)
            with open(local_file_location, "w") as f:
                f.write(output_gpd.to_json())
    except Exception as e:
        return f"Error reprojecting geojson {local_file_location}: {str(e)}"
    else:
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
        # print(path)
        # print(f"{'/'.join(path.split('/')[:-2])}/pmtiles)
        pmtiles_dir = os.path.join(str(Path(path).parents[1]), "pmtiles")
        geojson_file_name = Path(path.rsplit("/", 1)[-1])
        pmtiles_file_name = geojson_file_name.with_suffix(".pmtiles")
        s3_pmtiles_path_name = os.path.join(pmtiles_dir, pmtiles_file_name)[1:]
        # print(path, geojson_file_name, pmtiles_file_name, s3_pmtiles_path_name)
        # print(s3_pmtiles_path_name)
        error_str = download_file_from_url(
            layer_info["layer_url"], f"{data_dir}/{str(geojson_file_name)}"
        )
        if error_str:
            print("aaa")
            print(error_str)
            errors.append(error_str)
            continue
        print(reproject_geojson(f"{data_dir}/{str(geojson_file_name)}"))
        error_str = convert_geojson_to_pmtiles(
            [
                {
                    "file": f"{data_dir}/{geojson_file_name}",
                    "layer": f"{layer_info['layer_id']}",
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
        print(f"uploading to {s3_pmtiles_path_name}")
        error_str = upload_file_to_s3_bucket(
            f"{data_dir}/{pmtiles_file_name}", s3_bucket_name, s3_pmtiles_path_name
        )
        if error_str:
            print(error_str)
            errors.append(error_str)
            continue

    return errors


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
    s3_client = boto3.client("s3")
    # If city_ids is None, get a list of all city_ids
    city_ids = None
    if supplied_city_ids:
        city_ids = supplied_city_ids
    else:
        city_ids, error = get_city_ids()
        if error:
            print(error)
            return [error], failed_city_ids

    # Process each city ID
    for city_id in city_ids:
        if city_ids_to_skip and city_id in city_ids_to_skip:
            print(f"Skipping {city_ids_to_skip}")
            continue
        else:
            print(f"Processing {city_id}")
            # First check if it exists
        err, exists = file_exists_in_s3(
            s3_bucket_name, f"{destination_s3_path}/{city_id}.pmtiles"
        )
        if err:
            errors.append(err)
        if exists:
            continue

        # Download the geojson and store in the data_dir
        error_str = None
        data = None
        local_pmtiles_file_name = f"{data_dir}/{city_id}.pmtiles"

        try:
            url = urljoin(
                API_URL_DOMAIN,
                f"cities/{city_id}",
            )
            response = requests.get(url)
        except Exception as e:
            error_str = f"Error retrieving city details for city {city_id} : {str(e)}"
            continue
        city_details = response.json()
        admin_levels = city_details["admin_levels"]
        city_admin_level = city_details["city_admin_level"]

        geojsons_list = []
        for al in admin_levels:
            geojsons_list.append(
                {
                    "admin_level": al,
                    "geojson_path_with_file_name": f"{data_dir}/{city_id}__{al}.geojson",
                    "geojson_file_name": f"{city_id}__{al}.geojson",
                    "layer_name": al,
                }
            )
        layer_param_list = []
        city_admin_level_processed = False
        upload_to_s3 = True

        for gjd in geojsons_list:
            try:

                error = convert_geojson_urls_to_pmtiles(
                    data_dir,
                    [
                        f"https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/prd/boundaries/geojson/{city_id}__{gjd['admin_level']}.geojson"
                    ],
                    "wri-cities-data-api",
                    None,
                    False,
                    None,
                    True,
                )
                print(error)
                url = f"https://wri-cities-data-api.s3.us-east-1.amazonaws.com/data/prd/boundaries/geojson/{city_id}__{gjd['admin_level']}.geojson"
                print(url)
                # url = urljoin(
                #    API_URL_DOMAIN,
                #    f"cities/{city_id}/indicators/geojson?admin_level={gjd['admin_level']}",
                # )
                response = requests.get(url)
            except Exception as e:
                print(e)
                error_str = f"Error retrieving {gjd['admin_level']} geojson for city {city_id} : {str(e)}"
                errors.append(error_str)
                upload_to_s3 = False
                continue
            if response.status_code != 200:
                print(
                    f"Error retrieving {gjd['admin_level']} geojson for city {city_id} : Invalid response code : {response.status_code}"
                )
                if response.status_code != 200:
                    error_str = f"Error retrieving {gjd['admin_level']} geojson for city {city_id} : Invalid response code : {response.status_code}"
                errors.append(error_str)
                continue
                # print(error_str)
                failed_city_ids.append(city_id)
                upload_to_s3 = False
                break
            data = response.json()

            # with open(gjd["geojson_path_with_file_name"], "r") as f:
            #    data = json.load(f)
            if gjd["admin_level"] == city_admin_level:
                city_admin_level_processed = True
            features = data["features"]
            # Upload the geojson to s3
            print(f"Uploading geojson {city_id} to S3")
            # Prepare for the pmtiles generation
            for feature in features:
                properties = feature["properties"]
                if "geo_id" in properties:
                    properties["id"] = properties["geo_id"]
                for pname, pval in properties.copy().items():
                    if not isinstance(pval, dict):
                        # Not an indicator so continue
                        continue
                    else:
                        val = pval.get("value", None)
                        if not pval["value"]:
                            val = -999
                        properties[pname] = val

            with open(f'{gjd["geojson_path_with_file_name"]}.tmp', "w") as tmpf:
                json.dump(data, tmpf)
            # print(gjd["geojson_path_with_file_name"])
            # with open(gjd["geojson_path_with_file_name"], "w") as f:
            #     f.write(json.dumps(data, indent=2))
            # reproject_geojson(gjd["geojson_path_with_file_name"])
            # print(features)
            layer_param_list.append(
                {
                    "file": f'{gjd["geojson_path_with_file_name"]}.tmp',
                    "layer": gjd["layer_name"],
                }
            )
        if not upload_to_s3:
            print("Not uploading to S3")
            continue
        # Convert it to pmtimes
        print(layer_param_list)
        if layer_param_list and city_admin_level_processed:
            error = convert_geojson_to_pmtiles(
                layer_param_list, local_pmtiles_file_name, 13, "id"
            )
            if error:
                errors.append(error)
                print(error)
                failed_city_ids.append(city_id)
                continue

            # Upload the pmtiles to s3
            print(f"Uploading pmtiles {city_id} to S3")
            error = upload_file_to_s3_bucket(
                local_pmtiles_file_name,
                s3_bucket_name,
                f"{destination_s3_path}/pmtiles/{city_id}.pmtiles",
            )
            if error:
                print(error)
                errors.append(error)
                failed_city_ids.append(city_id)
                continue
        else:
            print(layer_param_list, city_admin_level_processed)

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
            print("Checking and fixing geojson projection")
            error = reproject_geojson(save_path)
            if error:
                print(error)
                errors.append(error)
            files_to_process.append(
                {
                    "filename_without_extension": file_name_without_extension,
                    "local_geojson_path_with_filename": save_path,
                    "pmtiles_file_name": pmtiles_file_name,
                    "destination_s3_dir": f"{parent_path}/pmtiles",
                    "destination_s3_path_with_filename": destination_s3_path_with_filename,
                }
            )
            destination_geojson_path = (
                f"{parent_path}/geojson/{file_name_without_extension}.geojson"
            )
            while destination_geojson_path[0] == "/":
                destination_geojson_path = destination_geojson_path[1:]
            print(
                "Uploading geojson to ",
                destination_geojson_path,
            )
            error = upload_file_to_s3_bucket(
                save_path,
                destination_s3_bucket,
                destination_geojson_path,
            )
            # print(error)
            if error:
                print(error)
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
