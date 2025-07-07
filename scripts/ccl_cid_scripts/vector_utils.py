import geopandas
import subprocess
import os
from typing import List, Union
from pathlib import Path
from urllib.parse import urlparse
from s3_utils import upload_file_to_s3_bucket
from network_utils import download_file_from_url


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
