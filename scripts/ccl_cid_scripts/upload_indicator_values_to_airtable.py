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
        # Setup the environment
        load_dotenv(".env.airtable")
        AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
        AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
        DATA_DIR = os.environ.get("DATA_DIR")
        if AIRTABLE_API_KEY is None or AIRTABLE_BASE_ID is None or DATA_DIR is None:
            raise Exception(
                "Please specify values for AIRTABLE_API_KEY, AIRTABLE_BASE_ID and DATA_DIR (a temporary working directory) in a .env.airtable file."
            )

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
    source_url = f"https://wri-cities-heat.s3.us-east-1.amazonaws.com/{city_id}/scenarios/aoi/{aoi_id}/cool-roofs/scenario-metrics.csv"
    dry_run = args.dry_run
    verbose = args.verbose
    err = upload_indicators(source_url, dry_run, verbose)
    if err:
        print(err)
        sys.exit(1)
    else:
        sys.exit(0)
"""
successful_combos = []
failed_combos = []

files = glob.glob("/Users/raghuram.bk/Downloads/aq3_metrics/ACC-6*_urbextbound.json")
for fn in files:
    filename_without_extn = os.path.splitext(os.path.basename(fn))[0]
    print("Processing ", filename_without_extn)
    parts = filename_without_extn.split("__")
    city_id = parts[1]
    aoi_id = "urban_extent"
    scenario_id = "baseline"
    cities_record = c_table.first(formula=match({"id": city_id}))
    if not cities_record:
        print("Could not find city ", city_id)
        # failed_combos.append(check_string)
        continue
    aoi_record = aoi_table.first(formula=match({"id": aoi_id}))
    if not aoi_record:
        print("Could not find aoi ", aoi_id)
        # failed_combos.append(check_string)
        continue
    scenarios_record = s_table.first(formula=match({"id": scenario_id}))
    if not scenarios_record:
        print("Could not find scenario ", scenario_id)
        # failed_combos.append(check_string)
        continue

    with open(fn, "r") as f:
        js = json.load(f)
        for k, v in js.items():
            parts = k.split("_")
            mode = parts[1]
            population_category = parts[2]
            indicator_id = f"AccessPopulationPercent_OpenSpace_{mode.title()}_{population_category.title()}"
            val = v["0"]
            # print(indicator_id, " : ", v["0"])

            indicator_record = i_table.first(formula=match({"id": indicator_id}))
            if not indicator_record:
                print("Could not find indicator ", indicator_id)
                # failed_combos.append(check_string)
                continue
            # print(val)
            if not val or val == "NA":
                val = -999
            else:
                val = float(val)
            id = f"{indicator_id}__{city_id}__{aoi_id}__{scenario_id}"
            try:
                formula = match({"id": id})
                existing_row = iv_table.first(
                    view="all",
                    formula=formula,
                )
                if existing_row:
                    print("found row!")
                    # print(existing_row["id"])
                    # print(id)
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
                            "application_id": "cid",
                        },
                    )
                    # sys.exit(0)
                else:
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
                            "application_id": "cid",
                        }
                    )
            except Exception as e:
                print("Failed to upload to airtable : ", str(e))
                print(k, v)
                continue
            # print(row["id"])
        # print(js)
sys.exit(0)
"""
"""
successful_combos = []
failed_combos = []
with open(
    "/Users/raghuram.bk/Downloads/ZAF-Cape_Town__business_district__street_trees__indicators.csv",
    # "/Users/raghuram.bk/Downloads/KEN_Nairobi__AccessPopulationPercent__indicators_values.csv",
    "r",
) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        print(row)

        print(row["cities_id"], row["areas_of_interest_id"])
        break
        check_string = f'{row["cities"]} {row["areas_of_interest_id"]}'
        # if check_string in failed_combos or check_string in successful_combos:
        #    continue
        # print("Processing ", row["cities"], row["areas_of_interest_id"])
        indicator_record = i_table.first(formula=match({"id": row["indicators_id"]}))
        if not indicator_record:
            print("Could not find indicator ", row["indicators_id"])
            failed_combos.append(check_string)
            continue
        cities_record = c_table.first(formula=match({"id": row["cities_id"]}))
        if not cities_record:
            print("Could not find city ", row["cities_id"])
            failed_combos.append(check_string)
            continue
        aoi_record = aoi_table.first(formula=match({"id": row["areas_of_interest_id"]}))
        if not aoi_record:
            print("Could not find aoi ", row["areas_of_interest_id"])
            failed_combos.append(check_string)
            continue
        scenarios_record = s_table.first(formula=match({"id": row["scenarios_id"]}))
        if not scenarios_record:
            print("Could not find scenario ", row["scenarios_id"])
            failed_combos.append(check_string)
            continue
        if row["value"] == "NA":
            val = -999
        else:
            val = float(row["value"])
        # print(row["id"])

        formula = match({"id": row["id"]})
        existing_row = iv_table.first(
            view="all",
            formula=formula,
        )
        try:
            if existing_row:
                print("found row!")
                iv_table.update(
                    existing_row["id"],
                    {
                        "indicators": [indicator_record["id"]],
                        "cities": [cities_record["id"]],
                        # "cities_id": row["cities_id"],
                        "areas_of_interest": [aoi_record["id"]],
                        # "areas_of_interest_id": row["areas_of_interest_id"],
                        "value": val,
                        "scenarios": [scenarios_record["id"]],
                        # "scenarios_id": row["scenarios_id"],
                        "time": row["time"],
                        "date": row["date"],
                        "application_id": row["application_id"],
                    },
                )
            else:
                iv_table.create(
                    {
                        "indicators": [indicator_record["id"]],
                        "cities": [cities_record["id"]],
                        # "cities_id": row["cities_id"],
                        "areas_of_interest": [aoi_record["id"]],
                        # "areas_of_interest_id": row["areas_of_interest_id"],
                        "value": val,
                        "scenarios": [scenarios_record["id"]],
                        # "scenarios_id": row["scenarios_id"],
                        "time": row["time"],
                        "date": row["date"],
                        "application_id": row["application_id"],
                    }
                )
        except Exception as e:
            print("Failed to upload to airtable : ", str(e))
            continue
        successful_combos.append(check_string)
print(failed_combos)
"""
