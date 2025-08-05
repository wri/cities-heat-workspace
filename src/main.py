import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window, from_bounds
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from rasterio.io import MemoryFile
from pathlib import Path
import requests
import yaml

"""
1)check higest and lowest points (pixel value) from the building-DSM and also retrieve the pixel location
2)do the same for DEMs
3)save the metrics as a quick .csv"""


def get_highest_and_lowest_points(dsm_path, dem_path):
    with rasterio.open(dsm_path) as src_dsm, rasterio.open(dem_path) as src_dem:
        dsm_data = src_dsm.read(1)
        dem_data = src_dem.read(1)
        dsm_transform = src_dsm.transform
        dem_transform = src_dem.transform
        dsm_crs = src_dsm.crs
        dem_crs = src_dem.crs

    # dsm
    tallest_bldg = np.max(dsm_data)
    tallest_bldg_location = np.where(dsm_data == tallest_bldg)
    # get one random location from the array of min and max
    random_idx = np.random.randint(0, len(tallest_bldg_location[0]))
    tallest_bldg_location = (tallest_bldg_location[0][random_idx], tallest_bldg_location[1][random_idx])

    lowest_bldg = np.min(dsm_data)
    lowest_bldg_location = np.where(dsm_data == lowest_bldg)
 
    random_idx = np.random.randint(0, len(lowest_bldg_location[0]))
    lowest_bldg_location = (lowest_bldg_location[0][random_idx], lowest_bldg_location[1][random_idx])
    
    # dem
    highest_ground = np.max(dem_data)
    highest_ground_location = np.where(dem_data == highest_ground)

    random_idx = np.random.randint(0, len(highest_ground_location[0]))
    highest_ground_location = (highest_ground_location[0][random_idx], highest_ground_location[1][random_idx])

    lowest_ground = np.min(dem_data)
    lowest_ground_location = np.where(dem_data == lowest_ground)

    random_idx = np.random.randint(0, len(lowest_ground_location[0]))
    lowest_ground_location = (lowest_ground_location[0][random_idx], lowest_ground_location[1][random_idx])

    # get coordinates for the pixel locations
    tb_row, tb_col = tallest_bldg_location[0], tallest_bldg_location[1]
    lb_row, lb_col = lowest_bldg_location[0], lowest_bldg_location[1]
    hg_row, hg_col = highest_ground_location[0], highest_ground_location[1]
    lg_row, lg_col = lowest_ground_location[0], lowest_ground_location[1]

    # convert to coordinates in native CRS
    tallest_bldg_coords = rasterio.transform.xy(dsm_transform, tb_row, tb_col, offset='center')
    lowest_bldg_coords = rasterio.transform.xy(dsm_transform, lb_row, lb_col, offset='center')
    highest_ground_coords = rasterio.transform.xy(dem_transform, hg_row, hg_col, offset='center')
    lowest_ground_coords = rasterio.transform.xy(dem_transform, lg_row, lg_col, offset='center')

    print(
          f"Tallest building: {tallest_bldg}m at {tallest_bldg_location}.\n"
          f"Lowest building: {lowest_bldg}m at {lowest_bldg_location}.\n"
          f"Highest ground: {highest_ground}m at {highest_ground_location}.\n"
          f"Lowest ground: {lowest_ground}m at {lowest_ground_location}."
    )
            
    return {
        "tallest_bldg": tallest_bldg,
        "tallest_bldg_pixel" : tallest_bldg_location,
        "tallest_bldg_coords": tallest_bldg_coords,
        "lowest_bldg": lowest_bldg, 
        "lowest_bldg_pixel": lowest_bldg_location,
        "lowest_bldg_coords": lowest_bldg_coords,
        "highest_ground": highest_ground,
        "highest_ground_pixel": highest_ground_location,
        "highest_ground_coords": highest_ground_coords,
        "lowest_ground": lowest_ground,
        "lowest_ground_pixel": lowest_ground_location,
        "lowest_ground_coords": lowest_ground_coords,
        "dem_crs": dem_crs,
        "dsm_crs": dsm_crs
    }



def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    
    output_dir = Path(f"result/height/metrics")
    output_dir.mkdir(parents = True, exist_ok = True)

    results = []

    for city_name, city_config in all_configs.items():
        print(f"\n==========Proecessing {city_name}==================")

        required_keys = {'dsm_path', 'dem_path'}
        if not all(k in city_config for k in required_keys):
            print(f"⚠️ Skipping {city_name}: incomplete configuration file.")
            continue

        dsm_path = city_config['dsm_path']
        dem_path = city_config['dem_path']
        
        # skip if paths are none
        if dsm_path is None or dem_path is None:
            print(f"⚠️ Skipping {city_name}: dsm_path or dem_path is None.")
            continue

        metrics = get_highest_and_lowest_points(dsm_path, dem_path)

        results.append({
            "City": city_name,
            "CRS": metrics["dem_crs"],
            "Tallest Building (m)": metrics["tallest_bldg"],
            "Tallest Building (pixel)": metrics["tallest_bldg_pixel"],
            "Tallest Building (coords)": metrics["tallest_bldg_coords"],
            "Lowest Building (m)": metrics["lowest_bldg"],
            "Lowest Building (pixel)": metrics["lowest_bldg_pixel"],
            "Lowest Building (coords)": metrics["lowest_bldg_coords"],
            "Highest Ground (m)": metrics["highest_ground"],
            "Highest Ground (pixel)": metrics["highest_ground_pixel"],
            "Highest Ground (coords)": metrics["highest_ground_coords"],
            "Lowest Ground (m)": metrics["lowest_ground"],
            "Lowest Ground (pixel)": metrics["lowest_ground_pixel"],
            "Lowest Ground (coords)": metrics["lowest_ground_coords"]
        })

    df = pd.DataFrame(results)
    df.to_csv(output_dir / "higest_lowest.csv", index = False)

    print("✅ Complete")

if __name__ == "__main__":
    main()

  
