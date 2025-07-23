import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from rasterio.io import MemoryFile
from pathlib import Path
import requests
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
import yaml
import sys
sys.path.append('src')
from visualization.building_height_viz import plot_building_height_validation


# TODO: this is the only one that calls the viz script in the validation script. maybe apply it for other scripts as well? 


def open_local_raster(file_path):
    return rasterio.open(file_path)


def get_overlap_window(src1, src2):
    if src1.crs != src2.crs:
        bounds2 = transform_bounds(src2.crs, src1.crs, *src2.bounds)
    else:
        bounds2 = src2.bounds

    overlap_bounds = BoundingBox(
        max(src1.bounds.left, bounds2.left),
        max(src1.bounds.bottom, bounds2.bottom),
        min(src1.bounds.right, bounds2.right),
        min(src1.bounds.top, bounds2.top)
    )

    if (overlap_bounds.right <= overlap_bounds.left) or (overlap_bounds.top <= overlap_bounds.bottom):
        raise ValueError("No overlapping region between rasters.")

    window1 = from_bounds(*overlap_bounds, transform=src1.transform)
    window2 = from_bounds(*overlap_bounds, transform=src2.transform)

    return window1.round_offsets(), window2.round_offsets()


def shrink_window(window, n_pixels):
    return Window(
        window.col_off + n_pixels,
        window.row_off + n_pixels,
        window.width - 2 * n_pixels,
        window.height - 2 * n_pixels
    )

def compute_metrics(name, local, global_, errors, total_pixels_local, total_pixels_global, signed = True):
    metrics = {
        "Filter_Type": name,
        "MAE": round(mean_absolute_error(local, global_), 4),
        "R²": round(r2_score(local, global_), 4),   
        "Mean_Bias": round(np.mean(errors), 4),
        "RMSE": round(np.sqrt(np.mean(errors**2)), 4),
        "STD": round(np.std(errors), 4),
        "Mean_Height_Local (m)": round(np.mean(local), 4), 
        "Mean_Height_Global (m)": round(np.mean(global_), 4),
        "90th Percentile Error (m)": round(np.percentile(errors, 90), 4),
        "95th Percentile Error (m)": round(np.percentile(errors, 95), 4),
        "Valid Pixels (%)": round(len(local) / total_pixels_local * 100, 4)
        # "% Valid Pixels Global": round(len(global_) / total_pixels_global * 100, 4),

    }

    if signed:
        positive_errors = errors[errors > 0]
        negative_errors = errors[errors < 0]
        metrics.update({
            "Mean_Overestimation (m)": round(np.mean(positive_errors) if len(positive_errors) > 0 else 0, 4),
            "Mean_Underestimation (m)": round(np.mean(negative_errors) if len(negative_errors) > 0 else 0, 4),
            "Overestimation (%)": round(len(positive_errors) / len(local) * 100, 4),
            "Underestimation (%)": round(len(negative_errors) / len(local) * 100, 4)
        })
    

    return metrics
    

def calculate_building_height_metrics(city, local_dsm, global_dsm, local_dem, global_dem, output_dir):
    with open_local_raster(local_dsm) as src_ldsm, open_local_raster(global_dsm) as src_gdsm, \
         open_local_raster(local_dem) as src_ldem, open_local_raster(global_dem) as src_gdem:

        if src_ldsm.transform != src_gdsm.transform or src_ldsm.shape != src_gdsm.shape:
            print("🟠 DSM mismatch. Cropping.")
            win_ldsm, win_gdsm = get_overlap_window(src_ldsm, src_gdsm)
            win_ldsm = shrink_window(win_ldsm, 10)
            win_gdsm = shrink_window(win_gdsm, 10)
            print(f"DSM Local Window: {win_ldsm}, DSM Global Window: {win_gdsm}")
        else:
            print("🟢 DSM aligned. Proceeding.")
            win_ldsm = win_gdsm = shrink_window(Window(0, 0, src_ldsm.width, src_ldsm.height), 10)

        dsm_local = src_ldsm.read(1, window=win_ldsm)
        dsm_global = src_gdsm.read(1, window=win_gdsm)
        print(f"DSM Local Shape: {dsm_local.shape}, DSM Global Shape: {dsm_global.shape}")

        win_ldem = win_ldsm
        win_gdem = win_gdsm

        dem_local = src_ldem.read(1, window=win_ldem)
        dem_global = src_gdem.read(1, window=win_gdem)
        print(f"DEM Local Shape: {dem_local.shape}, DEM Global Shape: {dem_global.shape}")

    # calculate height only 
    height_local = dsm_local - dem_local
    height_global = dsm_global - dem_global

    # print(f"Mean height local: {np.mean(height_local)}, mean height global: {np.mean(height_global)}")

    # mask for valid date (filtering out nodata)
    mask = np.isfinite(height_local) & np.isfinite(height_global)
    
    total_pixels_local = np.count_nonzero(np.isfinite(height_local))
    total_pixels_global = np.count_nonzero(np.isfinite(height_global))

    local_vals = height_local[mask].flatten()
    print(f"Number of local vals that are negative: {len(local_vals[local_vals < 0])}")
    global_vals = height_global[mask].flatten()
    print(f"Number of global vals that are negative: {len(global_vals[global_vals < 0])}")
    height_errors = global_vals - local_vals

    print("Min local_vals:", np.min(local_vals), "Max local_vals:", np.max(local_vals))
    print("Min global_vals:", np.min(global_vals), "Max global_vals:", np.max(global_vals))

    # for absolute results, calculate the absolute difference between local and global
    absolute_local = np.abs(local_vals)
    absolute_global = np.abs(global_vals)
    absolute_errors = absolute_global - absolute_local

    ### There are 4 different sets: unfiltered, z-score filtered, positive differences only, all differences incluidng negative
    # 1. unfiltered - positive & negative values 
    metrics_unfiltered_all = compute_metrics("Unfiltered (all)", local_vals, global_vals, height_errors, total_pixels_local, total_pixels_global, signed = True)

    # 2. unfiltered - positive only
    pos_mask = (local_vals > 0) & (global_vals > 0)
    metrics_unfiltered_pos = compute_metrics("Unfiltered (positive only)", local_vals[pos_mask], global_vals[pos_mask], height_errors[pos_mask], total_pixels_local, total_pixels_global, signed = True)

    # 3. z-score filtered - all
    z_score = (height_errors - np.mean(height_errors)) / np.std(height_errors)
    z_mask = (z_score > -3) & (z_score < 3)
    metrics_z_filtered_all = compute_metrics("Z-score filtered (all)", local_vals[z_mask], global_vals[z_mask], height_errors[z_mask], total_pixels_local, total_pixels_global, signed = True)

    # 4. z-score filtered - positive only
    final_mask = z_mask & (local_vals > 0) & (global_vals > 0)
    metrics_z_filtered_pos = compute_metrics("Z-score filtered (positive only)", local_vals[final_mask], global_vals[final_mask], height_errors[final_mask], total_pixels_local, total_pixels_global, signed = True)

    # 5. absolute results
    metrics_absolute = compute_metrics("Absolute results", absolute_local, absolute_global, absolute_errors, total_pixels_local, total_pixels_global, signed = False)

    all_metrics = [metrics_unfiltered_all, metrics_z_filtered_all, metrics_absolute, metrics_unfiltered_pos, metrics_z_filtered_pos]
    for m in all_metrics:
        m["City"] = city




    # save all metrics to a single csv
    pd.DataFrame(all_metrics).to_csv(output_dir / "building_height_metrics.csv", index=False)
    print(f"✅ Saved all building height metrics for {city} to {output_dir.resolve()}")

    print("Difference in abs local vs local:", np.sum(absolute_local != local_vals))
    print("Min local:", np.min(local_vals), "Min global:", np.min(global_vals))

    # calculate positive errors unfiltered
    positive_errors_unfiltered = height_errors[height_errors > 0]
    
    return {
        "local_filtered": local_vals[z_mask],
        "global_filtered": global_vals[z_mask],
        "height_errors_filtered": height_errors[z_mask],
        "height_errors": height_errors,
        "positive_errors_unfiltered": positive_errors_unfiltered,
        "metrics": metrics_z_filtered_all
    }


# check if files exist locally
def file_exists_locally(file_path):
    return Path(file_path).exists()

# download data from s3 if not locally available
def download_from_url(url, local_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {url} to {local_path}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)     

    # change the city name based on the city name in city_config.yaml   
    CITY_NAME = "RiodeJaneiro"

    if CITY_NAME not in all_configs:
        raise ValueError(f"{CITY_NAME} not found in config.")

    local_dsm_path = all_configs[CITY_NAME]['local_dsm_path']
    global_dsm_path = all_configs[CITY_NAME]['global_dsm_path']
    local_dem_path = all_configs[CITY_NAME]['local_dem_path']
    global_dem_path = all_configs[CITY_NAME]['global_dem_path']

    # Check if local files exist, otherwise download from URL
    if not file_exists_locally(local_dsm_path):
        download_from_url(all_configs[CITY_NAME]['url_local_dsm'], local_dsm_path)
    if not file_exists_locally(global_dsm_path):
        download_from_url(all_configs[CITY_NAME]['url_global_dsm'], global_dsm_path)
    if not file_exists_locally(local_dem_path):
        download_from_url(all_configs[CITY_NAME]['url_local_dem'], local_dem_path)
    if not file_exists_locally(global_dem_path):
        download_from_url(all_configs[CITY_NAME]['url_global_dem'], global_dem_path)

    # metrics calculation
    metrics_output_dir = Path(f"results/buildings/{CITY_NAME}/height/metrics")
    metrics_output_dir.mkdir(parents=True, exist_ok=True)

    result = calculate_building_height_metrics(CITY_NAME, local_dsm_path, global_dsm_path, local_dem_path, global_dem_path, metrics_output_dir)
    
    # # plots generation
    # # calls plot_building_height_validation from building_height_viz.py
    # plots_output_dir = Path(f"results/buildings/{CITY_NAME}/height/graphs")
    # plots_output_dir.mkdir(parents=True, exist_ok=True)
    
    # plots generation
    # calls plot_building_height_validation from building_height_viz.py
    plots_output_dir = Path(f"results/buildings/{CITY_NAME}/height/graphs")
    plots_output_dir.mkdir(parents=True, exist_ok=True)
    
    plot_building_height_validation(
        CITY_NAME, 
        result['local_filtered'], 
        result['global_filtered'], 
        result['height_errors_filtered'], 
        result['height_errors'],
        result['positive_errors_unfiltered'],
        result['metrics'], 
        plots_output_dir
    )


if __name__ == "__main__":
    main()