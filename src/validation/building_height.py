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

    # capture only the building pixels (building only dsm - dem)
    height_local = dsm_local - dem_local
    height_global = dsm_global - dem_global

    mask = np.isfinite(height_local) & np.isfinite(height_global)
    local_vals = height_local[mask].flatten()
    global_vals = height_global[mask].flatten()

    # errors between global and local 
    height_errors = global_vals - local_vals

    # filter outliers using z-score
    z_score = (height_errors - np.mean(height_errors)) / np.std(height_errors)
    # print("z-score: ", z_score)
    
    valid_mask_zscore = (z_score > -3) & (z_score < 3)

    # calculate positive/negative metrics
    positive_errors = height_errors[height_errors > 0]
    negative_errors = height_errors[height_errors < 0]

    # z-score filtered data
    local_filtered = local_vals[valid_mask_zscore]
    global_filtered = global_vals[valid_mask_zscore]
    height_errors_filtered = height_errors[valid_mask_zscore]

    positive_errors_filtered = height_errors_filtered[height_errors_filtered > 0]
    negative_errors_filtered = height_errors_filtered[height_errors_filtered < 0]

    # z-score filtered metrics
    mae_filtered = mean_absolute_error(local_filtered, global_filtered)
    r2_filtered = r2_score(local_filtered, global_filtered)
    mean_bias_filtered = np.mean(height_errors_filtered)
    std_filtered = np.std(height_errors_filtered)
    rmse_filtered = np.sqrt(np.mean(height_errors_filtered**2))

    # unfiltered metrics (using all valid finite data)
    mae_unfiltered = mean_absolute_error(local_vals, global_vals)
    r2_unfiltered = r2_score(local_vals, global_vals)
    mean_bias_unfiltered = np.mean(height_errors)
    std_unfiltered = np.std(height_errors)
    rmse_unfiltered = np.sqrt(np.mean(height_errors**2))

    metrics_zscore = {
        "City": city,
        "MAE": mae_filtered,
        "R²": r2_filtered,
        "Mean_Bias": mean_bias_filtered,
        "RMSE": rmse_filtered,
        "STD": std_filtered,
        "% Overestimation": len(positive_errors_filtered) / len(local_filtered) * 100,          
        "% Underestimation": len(negative_errors_filtered) / len(local_filtered) * 100,
        "Mean_Overestimation": np.mean(positive_errors_filtered) if len(positive_errors_filtered) > 0 else 0,
        "Mean_Underestimation": np.mean(negative_errors_filtered) if len(negative_errors_filtered) > 0 else 0,
        "% Valid Pixels": len(local_filtered)/len(height_local.flatten())*100,
        #"% Valid Pixels Global": len(global_filtered)/len(height_global.flatten())*100,
        "Filter_Type": "Z-score (±3)"
    }

    metrics_unfiltered = {
        "City": city,
        "MAE": mae_unfiltered,
        "R²": r2_unfiltered,
        "Mean_Bias": mean_bias_unfiltered,
        "RMSE": rmse_unfiltered,
        "STD": std_unfiltered,
        "% Overestimation": len(positive_errors) / len(local_vals) * 100,
        "% Underestimation": len(negative_errors) / len(local_vals) * 100,
        "Mean_Overestimation": np.mean(positive_errors) if len(positive_errors) > 0 else 0,
        "Mean_Underestimation": np.mean(negative_errors) if len(negative_errors) > 0 else 0,
        "% Valid Pixels": len(local_vals)/len(height_local.flatten())*100,
        #% Valid Pixels Global": len(global_vals)/len(height_global.flatten())*100,
        "Filter_Type": "None (all finite data)"
    }

    # save metrics to csv
    pd.DataFrame([metrics_zscore]).to_csv(output_dir / "building_height_metrics_filtered_by_zscore.csv", index=False)
    pd.DataFrame([metrics_unfiltered]).to_csv(output_dir / "building_height_metrics_unfiltered.csv", index=False)
    
    print(f"✅ Building height metrics calculated for {city}. Results saved to {output_dir.resolve()}")
    
    return {
        'local_filtered': local_filtered,
        'global_filtered': global_filtered,
        'height_errors_filtered': height_errors_filtered,
        'metrics': metrics_zscore
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
    CITY_NAME = "Monterrey3"

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
    
    # plots generation
    # calls plot_building_height_validation from building_height_viz.py
    plots_output_dir = Path(f"results/buildings/{CITY_NAME}/height/graphs")
    plots_output_dir.mkdir(parents=True, exist_ok=True)
    
    plot_building_height_validation(
        CITY_NAME, 
        result['local_filtered'], 
        result['global_filtered'], 
        result['height_errors_filtered'], 
        result['metrics'], 
        plots_output_dir
    )


if __name__ == "__main__":
    main()