import csv
from pyairtable import Api
from pyairtable.formulas import match
import sys
import glob
import json
import os
import argparse
from network_utils import download_file_from_url
from dotenv import load_dotenv
from urllib.parse import urlparse
from typing import Union


def upload_indicators(
    source_url: str, dry_run: bool, verbose: bool
) -> Union[str, None]:
    """
    Given a URL pointing to a csv file containing the indicator values
    in the pre-defined format, load them into airtable
    """
    try:
        url_components = urlparse(source_url)
        file_name = os.path.basename(url_components.path)
        local_file = os.path.join(DATA_DIR, file_name)
        err = download_file_from_url(source_url, local_file)
        if err:
            raise Exception(err)

        # Setup the API
        airtable_api = Api(AIRTABLE_API_KEY)

        # Setup the tables for processing
        iv_table = airtable_api.table(AIRTABLE_BASE_ID, "Indicators_values")
        i_table = airtable_api.table(AIRTABLE_BASE_ID, "Indicators")
        c_table = airtable_api.table(AIRTABLE_BASE_ID, "Cities")
        aoi_table = airtable_api.table(AIRTABLE_BASE_ID, "Areas_of_interest")
        s_table = airtable_api.table(AIRTABLE_BASE_ID, "Scenarios")

        # Now start loading
        with open(local_file, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            print("Processing ", source_url)

            # Used to store IDs whose validity have been checked so we dont use the API unnecessarily
            verified_scenario_ids = {}
            verified_indicator_ids = {}
            verified_cities_ids = {}
            verified_areas_of_interest_ids = {}

            for row in reader:
                if verbose:
                    print("Processing row ", row)
                if row["cities_id"] not in verified_cities_ids:
                    cities_record = c_table.first(
                        formula=match({"id": row["cities_id"]})
                    )
                    if not cities_record:
                        print("Could not find city ", row["cities_id"])
                        continue
                    else:
                        verified_cities_ids[row["cities_id"]] = cities_record["id"]
                        cities_id = cities_record["id"]

                if row["areas_of_interest_id"] not in verified_areas_of_interest_ids:
                    aoi_record = aoi_table.first(
                        formula=match({"id": row["areas_of_interest_id"]})
                    )
                    if not aoi_record:
                        print("Could not find aoi ", row["areas_of_interest_id"])
                        continue
                    else:
                        verified_areas_of_interest_ids[row["areas_of_interest_id"]] = (
                            aoi_record["id"]
                        )
                        areas_of_interest_id = aoi_record["id"]

                if row["scenarios_id"] not in verified_scenario_ids:
                    scenarios_record = s_table.first(
                        formula=match({"id": row["scenarios_id"]})
                    )
                    if not scenarios_record:
                        print("Could not find scenario ", row["scenarios_id"])
                        continue
                    else:
                        verified_scenario_ids[row["scenarios_id"]] = scenarios_record[
                            "id"
                        ]
                        scenario_id = scenarios_record["id"]

                if row["indicators_id"] not in verified_indicator_ids:
                    indicator_record = i_table.first(
                        formula=match({"id": row["indicators_id"]})
                    )
                    if not indicator_record:
                        print("Could not find indicator ", row["indicators_id"])
                        continue
                    else:
                        verified_indicator_ids[row["indicators_id"]] = indicator_record[
                            "id"
                        ]
                        indicator_id = indicator_record["id"]

                val = row["value"]
                # print(val)
                if not val or val == "NA":
                    val = -999
                else:
                    val = float(val)
                id = f"{row['indicators_id']}__{row['cities_id']}__{row['areas_of_interest_id']}__{row['scenarios_id']}"
                try:
                    formula = match({"id": id})
                    existing_row = iv_table.first(
                        view="all",
                        formula=formula,
                    )
                    if existing_row:
                        if verbose:
                            print("Will update existing row")
                        if dry_run:
                            continue
                        iv_table.update(
                            existing_row["id"],
                            {
                                "indicators": [indicator_record["id"]],
                                "cities": [cities_record["id"]],
                                "areas_of_interest": [aoi_record["id"]],
                                "value": val,
                                "scenarios": [scenarios_record["id"]],
                                "time": "NA",
                                "date": "NA",
                                "application_id": "ccl",
                            },
                        )
                        # sys.exit(0)
                    else:
                        if verbose:
                            print("Will insert new row")
                        if dry_run:
                            continue
                        iv_table.create(
                            {
                                "indicators": [indicator_record["id"]],
                                "cities": [cities_record["id"]],
                                "areas_of_interest": [aoi_record["id"]],
                                "value": val,
                                "scenarios": [scenarios_record["id"]],
                                "time": "NA",
                                "date": "NA",
                                "application_id": "ccl",
                            }
                        )
                except Exception as e:
                    print("Failed to upload to airtable : ", str(e))
                    continue
    except Exception as e:
        return f"Error uploading indicators: {str(e)}"
    else:
        return None


if __name__ == "__main__":

    # Setup the environment

    load_dotenv(".env")
    AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
    AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
    DATA_DIR = os.environ.get("DATA_DIR")
    if AIRTABLE_API_KEY is None or AIRTABLE_BASE_ID is None or DATA_DIR is None:
        raise Exception(
            "Please specify values for AIRTABLE_API_KEY, AIRTABLE_BASE_ID and DATA_DIR (a temporary working directory) in a .env.airtable file."
        )

    parser = argparse.ArgumentParser(
        description="Download a csv file from the specified URL and upload the values to airtable. Please specify values for AIRTABLE_API_KEY, AIRTABLE_BASE_ID and DATA_DIR (a temporary working directory) in a .env.airtable file.",
    )
    parser.add_argument(
        "-c",
        "--city_id",
        help="Specify the city_id for which the indicators need to be uploaded",
        action="store",
        dest="city_id",
        required=True,
    )
    parser.add_argument(
        "-a",
        "--aoi_id",
        help="Specify the aoi_id for which the indicators values need to be uploaded",
        action="store",
        dest="aoi_id",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--dry_run",
        help="Specify this argument to only check against the Airtable if all rows are ok and not update/insert any data.",
        default=False,
        action="store_true",
        dest="dry_run",
    )
    parser.add_argument(
        "-s",
        "--scenario",
        choices=["baseline", "cool-roofs", "street-trees", "park-shade-structures"],
        dest="scenario_id",
        help="Specify the scenario for which the layers need to be generated. If not specified, layers for all scenarios will be generated.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Specify this argument to print verbose messages.",
        default=False,
        action="store_true",
        dest="verbose",
    )
    args = parser.parse_args()
    city_id = args.city_id
    aoi_id = args.aoi_id
    scenario_id = args.scenario_id
    source_url = f"https://wri-cities-heat.s3.us-east-1.amazonaws.com/{city_id}/scenarios/aoi/{aoi_id}/{scenario_id}/scenario-metrics.csv"
    dry_run = args.dry_run
    verbose = args.verbose
    err = upload_indicators(source_url, dry_run, verbose)
    if err:
        print(err)
        sys.exit(1)
    else:
        sys.exit(0)
