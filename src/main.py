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

# TODO: ⚠️ add building points WITH the ground elevation as well.


def get_highest_and_lowest_points(dsm_path, dem_path):
    with rasterio.open(dsm_path) as src_dsm, rasterio.open(dem_path) as src_dem:
        dsm_data = src_dsm.read(1)
        dem_data = src_dem.read(1)
        dsm_transform = src_dsm.transform
        dem_transform = src_dem.transform
        dsm_crs = src_dsm.crs
        dem_crs = src_dem.crs

    # only leave the building heights in the dsm
    dsm_bldg_data = dsm_data - dem_data
    
    # filter only for heights greater than 0
    valid_mask = (dsm_bldg_data > 0) & (~np.isnan(dsm_bldg_data))
    dsm_bldg_data_filtered = dsm_bldg_data[valid_mask]
    
    # dsm - tallest and lowest building excluding the ground
    tallest_bldg = np.max(dsm_bldg_data_filtered)
    tallest_bldg_location = np.where(dsm_bldg_data == tallest_bldg)
    
    print(f"how many tallest bldg pixels? {tallest_bldg_location}")

    middle_idx_tb = len(tallest_bldg_location[0]) // 2
    tallest_bldg_location = (tallest_bldg_location[0][middle_idx_tb], tallest_bldg_location[1][middle_idx_tb])

    lowest_bldg = np.min(dsm_bldg_data_filtered)
    lowest_bldg_location = np.where(dsm_bldg_data == lowest_bldg) #use dsm_data for pixel location (2D array)
    print(f"Number of pixels with minimum building height ({lowest_bldg}m): {len(lowest_bldg_location[0])}")
 
    middle_idx_lb = len(lowest_bldg_location[0]) // 2
    lowest_bldg_location = (lowest_bldg_location[0][middle_idx_lb], lowest_bldg_location[1][middle_idx_lb])

    # dsm - tallest & lowest bldg including the ground
    tallest_bldg_ground = np.max(dsm_data)
    tallest_bldg_ground_location = np.where(dsm_data == tallest_bldg_ground)

    middle_idx_tb_ground = len(tallest_bldg_ground_location[0]) // 2
    tallest_bldg_ground_location = (tallest_bldg_ground_location[0][middle_idx_tb_ground], tallest_bldg_ground_location[1][middle_idx_tb_ground])   
    
    lowest_bldg_ground = np.min(dsm_data)
    lowest_bldg_ground_location = np.where(dsm_data == lowest_bldg_ground)

    middle_idx_lb_ground = len(lowest_bldg_ground_location[0]) // 2
    lowest_bldg_ground_location = (lowest_bldg_ground_location[0][middle_idx_lb_ground], lowest_bldg_ground_location[1][middle_idx_lb_ground])      

    # dem
    highest_ground = np.max(dem_data)
    highest_ground_location = np.where(dem_data == highest_ground)
    print(f"Number of pixels with maximum ground height ({highest_ground}m): {len(highest_ground_location[0])}")

    middle_idx_hg = len(highest_ground_location[0]) // 2
    highest_ground_location = (highest_ground_location[0][middle_idx_hg], highest_ground_location[1][middle_idx_hg])

    lowest_ground = np.min(dem_data)
    lowest_ground_location = np.where(dem_data == lowest_ground)
    print(f"Number of pixels with minimum ground height ({lowest_ground}m): {len(lowest_ground_location[0])}")

    middle_idx_lg = len(lowest_ground_location[0]) // 2
    lowest_ground_location = (lowest_ground_location[0][middle_idx_lg], lowest_ground_location[1][middle_idx_lg])

    # get coordinates for the pixel locations
    tb_row, tb_col = tallest_bldg_location[0], tallest_bldg_location[1]
    lb_row, lb_col = lowest_bldg_location[0], lowest_bldg_location[1]
    tb_row_ground, tb_col_ground = tallest_bldg_ground_location[0], tallest_bldg_ground_location[1]
    lb_row_ground, lb_col_ground = lowest_bldg_ground_location[0], lowest_bldg_ground_location[1]
    hg_row, hg_col = highest_ground_location[0], highest_ground_location[1]
    lg_row, lg_col = lowest_ground_location[0], lowest_ground_location[1]

    # convert to coordinates in native CRS
    tallest_bldg_coords = rasterio.transform.xy(dsm_transform, tb_row, tb_col, offset='center')
    lowest_bldg_coords = rasterio.transform.xy(dsm_transform, lb_row, lb_col, offset='center')
    tb_row_ground_coords, tb_col_ground_coords = rasterio.transform.xy(dsm_transform, tb_row_ground, tb_col_ground, offset='center')
    lb_row_ground_coords, lb_col_ground_coords = rasterio.transform.xy(dsm_transform, lb_row_ground, lb_col_ground, offset='center')
    highest_ground_coords = rasterio.transform.xy(dem_transform, hg_row, hg_col, offset='center')
    lowest_ground_coords = rasterio.transform.xy(dem_transform, lg_row, lg_col, offset='center')

    print(
          f"Tallest building: {tallest_bldg}m at {tallest_bldg_location}.\n"
          f"Lowest building: {lowest_bldg}m at {lowest_bldg_location}.\n"
          f"Tallest building (ground): {tallest_bldg_ground}m at {tallest_bldg_ground_location}.\n"
          f"Lowest building (ground): {lowest_bldg_ground}m at {lowest_bldg_ground_location}.\n"
          f"Highest ground: {highest_ground}m at {highest_ground_location}.\n"
          f"Lowest ground: {lowest_ground}m at {lowest_ground_location}."
    )
            
    return {
        "tallest_bldg": tallest_bldg,
        "tallest_bldg_pixel" : f"{int(tb_row)},{int(tb_col)}",
        "tallest_bldg_coords": f"{float(tallest_bldg_coords[0]):.2f},{float(tallest_bldg_coords[1]):.2f}",
        "lowest_bldg": lowest_bldg, 
        "lowest_bldg_pixel": f"{int(lb_row)},{int(lb_col)}",
        "lowest_bldg_coords": f"{float(lowest_bldg_coords[0]):.2f},{float(lowest_bldg_coords[1]):.2f}",
        "tallest_bldg_ground": tallest_bldg_ground,
        "tallest_bldg_ground_pixel": f"{int(tb_row_ground)},{int(tb_col_ground)}",
        "tallest_bldg_ground_coords": f"{float(tb_row_ground_coords):.2f},{float(tb_col_ground_coords):.2f}",
        "lowest_bldg_ground": lowest_bldg_ground,
        "lowest_bldg_ground_pixel": f"{int(lb_row_ground)},{int(lb_col_ground)}",
        "lowest_bldg_ground_coords": f"{float(lb_row_ground_coords):.2f},{float(lb_col_ground_coords):.2f}",
        "highest_ground": highest_ground,
        "highest_ground_pixel": f"{int(hg_row)},{int(hg_col)}",
        "highest_ground_coords": f"{float(highest_ground_coords[0]):.2f},{float(highest_ground_coords[1]):.2f}",
        "lowest_ground": lowest_ground,
        "lowest_ground_pixel": f"{int(lg_row)},{int(lg_col)}",
        "lowest_ground_coords": f"{float(lowest_ground_coords[0]):.2f},{float(lowest_ground_coords[1]):.2f}",
        "dem_crs": dem_crs,
        "dsm_crs": dsm_crs
    }



def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    
    output_dir = Path(f"result/height/metrics")
    output_dir.mkdir(parents = True, exist_ok = True)

    results = []
    main_results = []

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
            "Tallest Building (ground) (m)": metrics["tallest_bldg_ground"],
            "Tallest Building (ground) (pixel)": metrics["tallest_bldg_ground_pixel"],
            "Tallest Building (ground) (coords)": metrics["tallest_bldg_ground_coords"],
            "Lowest Building (ground) (m)": metrics["lowest_bldg_ground"],
            "Lowest Building (ground) (pixel)": metrics["lowest_bldg_ground_pixel"],
            "Lowest Building (ground) (coords)": metrics["lowest_bldg_ground_coords"],
            "Highest Ground (m)": metrics["highest_ground"],
            "Highest Ground (pixel)": metrics["highest_ground_pixel"],
            "Highest Ground (coords)": metrics["highest_ground_coords"],
            "Lowest Ground (m)": metrics["lowest_ground"],
            "Lowest Ground (pixel)": metrics["lowest_ground_pixel"],
            "Lowest Ground (coords)": metrics["lowest_ground_coords"]
        })

        main_results.append({
            "City": city_name,
            "CRS": metrics["dem_crs"],
            "Tallest Building (m)": metrics["tallest_bldg"],
            "Lowest Building (m)": metrics["lowest_bldg"],
            "Building Difference (m)": metrics["tallest_bldg"] - metrics["lowest_bldg"],
            "Tallest Building (ground) (m)": metrics["tallest_bldg_ground"],
            "Lowest Building (ground) (m)": metrics["lowest_bldg_ground"],
            "Building Difference (ground) (m)": metrics["tallest_bldg_ground"] - metrics["lowest_bldg_ground"],
            "Highest Ground (m)": metrics["highest_ground"],
            "Lowest Ground (m)": metrics["lowest_ground"],
            "Ground Difference (m)": metrics["highest_ground"] - metrics["lowest_ground"]
        })

    metrics_df = pd.DataFrame(results)
    metrics_df.to_csv(output_dir / "highest_lowest.csv", index = False)

    main_metrics_df = pd.DataFrame(main_results)
    main_metrics_df.to_csv(output_dir / "difference_metrics.csv", index = False)

    print("✅ Complete")

if __name__ == "__main__":
    main()

  
