import os
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Union
import argparse
from dotenv import load_dotenv
from api_utils import get_aggregated_layer_info
from network_utils import download_file_from_url
from vector_utils import reproject_geojson, convert_geojson_to_pmtiles
from s3_utils import upload_file_to_s3_bucket


def generate_pmtiles_for_layers(
    s3_bucket_name: str,
    data_dir: str,
    layer_ids: Union[List[str], None],
    city_ids: Union[List[str], None],
) -> List[str]:
    """
    Given a bucket and some layer IDS/layer URLS/city IDS, a working dir
    and an s3 bucket download the appropriate geojsons from the layer URLs,
    convert them to pmtiles and upload them back to the s3 bucket.

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
        if not dry_run:
            print(f"uploading to {s3_pmtiles_path_name}")
            error_str = upload_file_to_s3_bucket(
                f"{data_dir}/{pmtiles_file_name}", s3_bucket_name, s3_pmtiles_path_name
            )
            if error_str:
                print(error_str)
                errors.append(error_str)
                continue

    return errors


if __name__ == "__main__":

    load_dotenv()
    data_dir = os.environ.get("DATA_DIR")
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d", "--dry_run", default=False, action="store_true", dest="dry_run"
    )
    parser.add_argument(
        "-c",
        "--cities",
        action="extend",
        nargs="+",
        dest="city_ids",
    )
    parser.add_argument(
        "-l",
        "--layers",
        action="extend",
        nargs="+",
        dest="layer_ids",
    )
    args = parser.parse_args()
    dry_run = args.dry_run
    city_ids = args.city_ids
    layer_ids = args.layer_ids
