import os
import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
import yaml
from sklearn.metrics import mean_absolute_error, r2_score
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
import requests

def classify_raster(data):
    shade_classes = {0.00: 0, 0.03: 1, 1.00: 2}
    classified = np.full(data.shape, -1, dtype=np.int8)
    for val, label in shade_classes.items():
        mask = np.isclose(data, val, atol=0.0005)
        classified[mask] = label
    return classified

def get_overlap_window(srcs):
    # accepts a list of rasterio datasets, returns a window for each cropped to the overlap
    bounds = [s.bounds for s in srcs]
    crs = srcs[0].crs
    # transform all bounds to the first raster's CRS if needed
    for i, s in enumerate(srcs):
        if s.crs != crs:
            bounds[i] = transform_bounds(s.crs, crs, *s.bounds)
    overlap_bounds = BoundingBox(
        max(b.left for b in bounds),
        max(b.bottom for b in bounds),
        min(b.right for b in bounds),
        min(b.top for b in bounds)
    )
    if (overlap_bounds.right <= overlap_bounds.left) or (overlap_bounds.top <= overlap_bounds.bottom):
        raise ValueError("No overlapping region between rasters.")
    windows = [from_bounds(*overlap_bounds, transform=s.transform).round_offsets() for s in srcs]
    return windows

def shrink_window(window, n_pixels):
    return Window(
        window.col_off + n_pixels,
        window.row_off + n_pixels,
        window.width - 2 * n_pixels,
        window.height - 2 * n_pixels
    )

def compute_stats(y_true, y_pred):
    return {
        # 'MAE': round(mean_absolute_error(y_true, y_pred), 4),
        # 'R2': round(r2_score(y_true, y_pred), 4),
        'Mean Error (global - local)': round(round(np.mean(y_pred), 4) - round(np.mean(y_true), 4), 4),
        'Min True (local)': round(np.min(y_true), 4),
        'Max True (local)': round(np.max(y_true), 4),
        'Mean True (local)': round(np.mean(y_true), 4),
        'Median True (local)': round(np.median(y_true), 4),
        'Std True (local)': round(np.std(y_true), 4),
        'Min Pred (global)': round(np.min(y_pred), 4),
        'Max Pred (global)': round(np.max(y_pred), 4),
        'Mean Pred (global)': round(np.mean(y_pred), 4),
        'Median Pred (global)': round(np.median(y_pred), 4),
        'Std Pred (global)': round(np.std(y_pred), 4)
    }

def validate_utci_from_config(city, local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global, output_dir):
    # Use the provided paths and output_dir for validation
    print(f"Validating UTCI for {city}")
    
    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_utci_paths]
    stats_results = []
    
    for time, local_path, global_path, shade_path_local, shade_path_global in zip(base_time_steps, local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global, rasterio.open(shade_path_local) as src_shade_local, rasterio.open(shade_path_global) as src_shade_global:
                print(f"[DEBUG] Local shape, bounds, transform: {src_local.shape}, {src_local.bounds}, {src_local.transform}")
                print(f"[DEBUG] Global shape, bounds, transform: {src_global.shape}, {src_global.bounds}, {src_global.transform}")
                print(f"[DEBUG] Local Shade shape, bounds, transform: {src_shade_local.shape}, {src_shade_local.bounds}, {src_shade_local.transform}")
                print(f"[DEBUG] Global Shade shape, bounds, transform: {src_shade_global.shape}, {src_shade_global.bounds}, {src_shade_global.transform}")
                
                aligned = (
                    src_local.crs == src_global.crs == src_shade_local.crs == src_shade_global.crs and
                    src_local.transform == src_global.transform == src_shade_local.transform == src_shade_global.transform and
                    src_local.shape == src_global.shape == src_shade_local.shape == src_shade_global.shape and
                    src_local.bounds == src_global.bounds == src_shade_local.bounds == src_shade_global.bounds
                )
                
                if not aligned:
                    print(f"🟠 {time}: Raster mismatch. Cropping to overlap and trimming boundary.")
                    win_local, win_global, win_shade_local, win_shade_global = get_overlap_window([src_local, src_global, src_shade_local, src_shade_global])
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    win_shade_local = shrink_window(win_shade_local, 10)
                    win_shade_global = shrink_window(win_shade_global, 10)
                    local_data = src_local.read(1, window=win_local)
                    global_data = src_global.read(1, window=win_global)
                    raw_shade_data_local = src_shade_local.read(1, window=win_shade_local)
                    raw_shade_data_global = src_shade_global.read(1, window=win_shade_global)
                else:
                    print(f"🟢 {time}: Rasters aligned. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local_data = src_local.read(1, window=window)
                    global_data = src_global.read(1, window=window)
                    raw_shade_data_local = src_shade_local.read(1, window=window)
                    raw_shade_data_global = src_shade_global.read(1, window=window)
        
        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue
        

        # classify shade data from raw values to class labels
        shade_data_local = classify_raster(raw_shade_data_local)
        shade_data_global = classify_raster(raw_shade_data_global)

        # mask for valid data (valid in pixel)
        valid_mask = (~np.isnan(local_data)) & (~np.isnan(global_data))

        # # show shade data distribution (here, based on local shade data!)
        # unique_raw_values = np.unique(raw_shade_data_local[~np.isnan(raw_shade_data_local)])
        # unique_classified_values = np.unique(shade_data_local[shade_data_local != -1])
        # print(f"[DEBUG] {time}: Raw shade values: {unique_raw_values}")
        # print(f"[DEBUG] {time}: Classified shade values: {unique_classified_values}")
        # print(f"[DEBUG] {time}: Valid pixels %: {np.sum(valid_mask)/np.sum(~np.isnan(local_data))*100}")
       
        # all area 
        y_true = local_data[valid_mask].flatten()
        y_pred = global_data[valid_mask].flatten()
        stats = compute_stats(y_true, y_pred)
        stats_results.append({'Time': time, 'Mask': 'Whole Area', **stats})
        
        # shade (building and tree) 
        shade_mask_local = valid_mask & ((shade_data_local == 0) | (shade_data_local == 1))
        shade_mask_global = valid_mask & ((shade_data_global == 0) | (shade_data_global == 1))
        # Check if there are any valid pixels in both local and global masks
        if np.any(shade_mask_local) and np.any(shade_mask_global):
            y_true_shade = local_data[shade_mask_local].flatten()
            y_pred_shade = global_data[shade_mask_global].flatten()
            stats = compute_stats(y_true_shade, y_pred_shade)
            stats_results.append({'Time': time, 'Mask': 'Shade (Building and Tree)', **stats})
        else:
            print(f"⚠️  {time}: No shade pixels found")
       
        # no shade 
        noshade_mask_local   = valid_mask & (shade_data_local == 2)
        noshade_mask_global = valid_mask & (shade_data_global == 2)
        if np.any(noshade_mask_local) and np.any(noshade_mask_global):
            y_true_noshade = local_data[noshade_mask_local].flatten()
            y_pred_noshade = global_data[noshade_mask_global].flatten()
            stats = compute_stats(y_true_noshade, y_pred_noshade)
            stats_results.append({'Time': time, 'Mask': 'No Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'No Shade' pixels found")
        
        # building shade 
        bldg_mask_local = valid_mask & (shade_data_local == 0)
        bldg_mask_global = valid_mask & (shade_data_global == 0)
        if np.any(bldg_mask_local) and np.any(bldg_mask_global):
            y_true_bldg = local_data[bldg_mask_local].flatten()
            y_pred_bldg = global_data[bldg_mask_global].flatten()
            stats = compute_stats(y_true_bldg, y_pred_bldg)
            stats_results.append({'Time': time, 'Mask': 'Building Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Building Shade' pixels found")
        
        # tree shade 
        tree_mask_local = valid_mask & (shade_data_local == 1)
        tree_mask_global = valid_mask & (shade_data_global == 1)
        if np.any(tree_mask_local) and np.any(tree_mask_global):
            y_true_tree = local_data[tree_mask_local].flatten()
            y_pred_tree = global_data[tree_mask_global].flatten()
            stats = compute_stats(y_true_tree, y_pred_tree)
            stats_results.append({'Time': time, 'Mask': 'Tree Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Tree Shade' pixels found")

        # overlapping shade statistics

        # Define shade type names
        shade_type_names = {0: 'Building Shade', 1: 'Tree Shade', 2: 'No Shade'}

        # Initialize a list to store results
        overlapping_shade_results = []

        # Check for differences in UTCI values for matching shade classes (local vs global)
        for i in range(3):  # local and global shade classes: 0, 1, 2
            class_mask_local = (shade_data_local == i) & valid_mask
            class_mask_global = (shade_data_global == i) & valid_mask
            combined_mask = class_mask_local & class_mask_global
            
            if np.any(combined_mask):
                local_values = local_data[combined_mask]
                global_values = global_data[combined_mask]
                differences = local_values - global_values
                non_zero_differences = differences[differences != 0]
                no_differences = len(differences[differences == 0])
                total_pixels = len(local_values)
                num_differences = len(non_zero_differences)
                percentage_differences = round((num_differences / total_pixels) * 100, 4)
                
                # Calculate additional statistics
                min_diff = round(np.min(differences), 4)
                median_diff = round(np.median(differences), 4)
                max_diff = round(np.max(differences), 4)
                std_diff = round(np.std(differences), 4)
                
                # Calculate percentage of overlapping pixels relative to local shade type
                total_local_shade_pixels = np.sum(class_mask_local)
                percentage_overlapping = round((combined_mask.sum() / total_local_shade_pixels) * 100, 4)
                
                # Append results to the list
                overlapping_shade_results.append({
                    'Shade Type': shade_type_names[i],
                    'No Differences (number of pixels)': no_differences,
                    'Percentage Non-zero Differences (%)': percentage_differences,
                    'Percentage Overlapping (%)': percentage_overlapping,
                    'Min Difference (local - global)': min_diff,
                    'Median Difference (local - global)': median_diff,
                    'Max Difference (local - global)': max_diff,
                    'Std Difference': std_diff
                })

        # Convert the list to a DataFrame
        overlapping_shade_df = pd.DataFrame(overlapping_shade_results)

        # Save the DataFrame to a CSV file
        overlapping_shade_df.to_csv(output_dir / f"utci_overlapping_shade_{city}.csv", index=False)

        print(f"✅ Overlapping shade results saved to {output_dir / f'utci_overlapping_shade_{city}.csv'}")


    pd.DataFrame(stats_results).to_csv(output_dir / f"utci_stats_{city}.csv", index=False)
    print(f"✅ UTCI validation complete for {city}. Results saved to {output_dir.resolve()}")

# check if files exist locally
def file_exists_locally(file_path):
    return Path(file_path).exists()

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
    
    city_name = "Monterrey3"
    config = {"city": city_name, **all_configs[city_name]}

    # Select paths
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    shade_paths_local = config['shade_local_paths']
    shade_paths_global = config['shade_global_paths']

    # Debug: Print paths to verify
    print("Local UTCI Paths:", local_utci_paths)
    print("Global UTCI Paths:", global_utci_paths)

    # Check if any path contains '_20m'
    is_20m = any('_20m' in path for path in local_utci_paths + global_utci_paths)

    # Debug: Print the result of is_20m
    print("Is 20m data:", is_20m)

    # Set the output directory
    output_dir = Path(f"results/utci/{city_name}/20m/metrics") if is_20m else Path(f"results/utci/{city_name}/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Debug: Print the output directory
    print("Output Directory:", output_dir)

    # # Check if local files exist, otherwise download from URL
    # for local_path, global_path, shade_path_local, shade_path_global in zip(local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global):
    #     if not file_exists_locally(local_path):
    #         download_from_url(config['utci_local'], local_path)
    #     if not file_exists_locally(global_path):
    #         download_from_url(config['utci_global'], global_path)
    #     if not file_exists_locally(shade_path_local):
    #         download_from_url(config['shade_local'], shade_path_local)
    #     if not file_exists_locally(shade_path_global):
    #         download_from_url(config['shade_global'], shade_path_global)

    # Determine if the paths are for 20m data
    # is_20m = any('_20m' in path for path in local_utci_paths + global_utci_paths)

    # Set the output directory
    # output_dir = Path(f"results/utci/{city_name}/20m/metrics") if is_20m else Path(f"results/utci/{city_name}/metrics")
    # output_dir.mkdir(parents=True, exist_ok=True)

    # Pass the city name, paths, and output directory to the validation function
    validate_utci_from_config(city_name, local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global, output_dir)

if __name__ == "__main__":
    main() 




