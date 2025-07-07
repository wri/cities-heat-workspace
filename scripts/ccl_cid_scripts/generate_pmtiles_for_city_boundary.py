from typing import List, Tuple, Union
import os
import sys
import requests
import json
import argparse
from urllib.parse import urljoin
from dotenv import load_dotenv
from s3_utils import file_exists_in_s3, upload_file_to_s3_bucket
from api_utils import get_city_ids
from vector_utils import convert_geojson_to_pmtiles


def generate_pmtiles_for_city_boundary(
    s3_bucket_name: str,
    data_dir: str,
    destination_s3_path_prefix: str,
    supplied_city_ids: Union[List[str], None],
    city_ids_to_skip: Union[List[str], None],
    s3_base_url: str,
    api_url_domain: str,
    dry_run: str,
) -> Tuple[List[str], List[str]]:
    """
    Given an S3 bucket name, a destination s3 path and a list of city IDs (or None if
    for all city IDs), download the geojson for all the admin levels per city, convert
    it into pmtiles format and upload it to s3. Return a list of errors that happened
    along the way or an empty list if none happened.
    ### Args:
        s3_bucket_name - s3 bucket from where to download/upload files
        data_dir - a local dir where to store data and work on them
        destination_s3_path_prefix - the dir path in s3 to where the boundaries folder is located where the results should be stored.
        supplied_city_ids - List of cities for which files need to be constructed. If None, it will do it for all cities from the cities endpoint
        city_ids_to_skip - List of cities which should not be processed
        s3_base_url - The domain name of the url with the https prefix used to access the geojson files
        api_url_domain - The domain name of the url used to access the CCL/CID API endpoints

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
        city_ids, error = get_city_ids(api_url_domain)
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
        destination_pmtiles_path = os.path.join(
            destination_s3_path_prefix, "/boundaries/pmtiles/{city_id}.pmtiles"
        )
        err, exists = file_exists_in_s3(s3_bucket_name, destination_pmtiles_path)
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
                api_url_domain,
                f"cities/{city_id}",
            )
            response = requests.get(url)
        except Exception as e:
            error_str = f"Error retrieving city details for city {city_id} : {str(e)}"
            continue
        city_details = response.json()
        # print(city_details)
        admin_levels = city_details["admin_levels"]
        # city_admin_level = city_details["city_admin_level"]

        geojsons_list = []
        for al in admin_levels:
            geojsons_list.append(
                {
                    "admin_level": al,
                    "geojson_path_with_file_name": os.path.join(
                        data_dir, f"{city_id}__{al}.geojson"
                    ),
                    "geojson_file_name": f"{city_id}__{al}.geojson",
                    "layer_name": al,
                }
            )
        layer_param_list = []
        # city_admin_level_processed = False
        upload_to_s3 = True

        for gjd in geojsons_list:
            try:
                _path = os.path.join(
                    destination_s3_path_prefix,
                    f"boundaries/geojson/{city_id}__{gjd['admin_level']}.geojson",
                )
                url = urljoin(
                    s3_base_url,
                    _path,
                )
                print("url ", url)
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
                # continue
                # print(error_str)
                failed_city_ids.append(city_id)
                upload_to_s3 = False
                break
            data = response.json()

            # if gjd["admin_level"] == city_admin_level:
            #    city_admin_level_processed = True
            features = data["features"]
            # Upload the geojson to s3
            # print(f"Uploading geojson {city_id} to S3")
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
        # print(layer_param_list)
        # if layer_param_list and city_admin_level_processed:
        if layer_param_list:
            error = convert_geojson_to_pmtiles(
                layer_param_list, local_pmtiles_file_name, 13, "id"
            )
            if error:
                errors.append(error)
                print(error)
                failed_city_ids.append(city_id)
                continue

            upload_path = os.path.join(
                destination_s3_path_prefix,
                f"boundaries/pmtiles/{city_id}.pmtiles",
            )
            # print("upload path ", upload_path)
            if not dry_run:
                # Upload the pmtiles to s3
                print(f"Uploading pmtiles {city_id} to S3")
                error = upload_file_to_s3_bucket(
                    local_pmtiles_file_name, s3_bucket_name, upload_path
                )
                if error:
                    print(error)
                    errors.append(error)
                    failed_city_ids.append(city_id)
                    continue
        else:
            # print(layer_param_list, city_admin_level_processed)
            print(layer_param_list)

    return errors, failed_city_ids


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="",
    )
    parser.add_argument(
        "-d", "--dry_run", default=False, action="store_true", dest="dry_run"
    )
    parser.add_argument(
        "-c",
        "--cities_to_process",
        action="extend",
        nargs="+",
        dest="supplied_city_ids",
    )
    parser.add_argument(
        "-s", "--cities_to_skip", action="extend", nargs="+", dest="city_ids_to_skip"
    )

    args = parser.parse_args()
    supplied_city_ids = args.supplied_city_ids
    city_ids_to_skip = args.city_ids_to_skip
    if supplied_city_ids and city_ids_to_skip:
        print(
            "You can only specify either the city IDs to process or city IDs to skip and not both."
        )
        sys.exit(1)

    dry_run = args.dry_run
    load_dotenv(".env")

    s3_base_url = os.environ.get("DESTINATION_S3_BASE_URL")
    s3_bucket_name = os.environ.get("DESTINATION_S3_BUCKET")
    s3_path_prefix = os.environ.get("DESTINATION_S3_PATH_PREFIX")
    api_url_domain = os.environ.get("API_URL_DOMAIN")
    data_dir = os.environ.get("DATA_DIR")
    # print(os.environ)

    if s3_base_url is None or s3_bucket_name is None or s3_path_prefix is None:
        print(
            "Please specify DESTINATION_S3_BASE_URL, DESTINATION_S3_BUCKET, DESTINATION_S3_PATH_PREFIX, API_URL_DOMAIN in .env.s3"
        )
        sys.exit(1)

    errors, failed_cities = generate_pmtiles_for_city_boundary(
        s3_bucket_name,
        data_dir,
        s3_path_prefix,
        supplied_city_ids,
        city_ids_to_skip,
        s3_base_url,
        api_url_domain,
        dry_run,
    )
    if errors:
        print("Error generating boundary pmtiles for ", ",'.join(failed_cities)")
    else:
        print("Successfully generated boundary pmtiles.")
