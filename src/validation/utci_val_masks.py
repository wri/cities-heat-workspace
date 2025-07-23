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

def validate_utci_from_config(city, local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global, mask_path, mask_name, output_dir):
    print(f"Validating UTCI for {city}")
    print(f"   Local UTCI paths: {local_utci_paths}")
    print(f"   Global UTCI paths: {global_utci_paths}")
    print(f"   Local shade paths: {shade_paths_local}")
    print(f"   Global shade paths: {shade_paths_global}")
    print(f"   Mask path: {mask_path}")
    
    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_utci_paths]
    print(f"   Time steps to process: {base_time_steps}")
    
    stats_results = []
    overlapping_shade_results = []  
    for time, local_path, global_path, shade_path_local, shade_path_global in zip(base_time_steps, local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global):
        print(f"Processing {time}: {local_path} vs {global_path}")
        print(f"   Checking if files exist...")
        print(f"     Local UTCI: {Path(local_path).exists()}")
        print(f"     Global UTCI: {Path(global_path).exists()}")
        print(f"     Local shade: {Path(shade_path_local).exists()}")
        print(f"     Global shade: {Path(shade_path_global).exists()}")
        print(f"     Mask: {Path(mask_path).exists()}")
        try:
            with rasterio.open(local_path) as src_local, \
                 rasterio.open(global_path) as src_global, \
                 rasterio.open(shade_path_local) as src_shade_local, \
                 rasterio.open(shade_path_global) as src_shade_global, \
                 rasterio.open(mask_path) as src_mask:
                aligned = (
                    src_local.crs == src_global.crs == src_shade_local.crs == src_shade_global.crs == src_mask.crs and
                    src_local.transform == src_global.transform == src_shade_local.transform == src_shade_global.transform == src_mask.transform and
                    src_local.shape == src_global.shape == src_shade_local.shape == src_shade_global.shape == src_mask.shape and
                    src_local.bounds == src_global.bounds == src_shade_local.bounds == src_shade_global.bounds == src_mask.bounds
                )
                if not aligned:
                    print(f"🟠 {time}: Raster mismatch. Cropping to overlap and trimming boundary.")
                    win_local, win_global, win_shade_local, win_shade_global, win_mask = get_overlap_window([src_local, src_global, src_shade_local, src_shade_global, src_mask])
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    win_shade_local = shrink_window(win_shade_local, 10)
                    win_shade_global = shrink_window(win_shade_global, 10)
                    win_mask = shrink_window(win_mask, 10)
                    local_data = src_local.read(1, window=win_local)
                    global_data = src_global.read(1, window=win_global)
                    raw_shade_data_local = src_shade_local.read(1, window=win_shade_local)
                    raw_shade_data_global = src_shade_global.read(1, window=win_shade_global)
                    mask_data_cropped = src_mask.read(1, window=win_mask)
                else:
                    print(f"🟢 {time}: Rasters aligned. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local_data = src_local.read(1, window=window)
                    global_data = src_global.read(1, window=window)
                    raw_shade_data_local = src_shade_local.read(1, window=window)
                    raw_shade_data_global = src_shade_global.read(1, window=window)
                    mask_data_cropped = src_mask.read(1, window=window)
        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue
       
        # use mask raster (pedestrian or non_building)
        mask_valid = (mask_data_cropped == 1) # binary masks
        valid_mask = (local_data != -1) & (global_data != -1)
        combined_mask = valid_mask & mask_valid
        
        # apply combined_mask to all rasters before further analysis
        local_data_masked = np.where(combined_mask, local_data, -1)
        global_data_masked = np.where(combined_mask, global_data, -1)
        shade_data_local = classify_raster(np.where(combined_mask, raw_shade_data_local, np.nan))
        shade_data_global = classify_raster(np.where(combined_mask, raw_shade_data_global, np.nan))
        mask = (local_data_masked != -1) & (global_data_masked != -1)
        
        # all area
        y_true = local_data_masked[mask].flatten()
        y_pred = global_data_masked[mask].flatten()
        stats = compute_stats(y_true, y_pred)
        stats_results.append({'Time': time, 'Mask': 'Whole Area', **stats})
       
        # shade (building and tree)
        shade_mask_local = mask & ((shade_data_local == 0) | (shade_data_local == 1))
        shade_mask_global = mask & ((shade_data_global == 0) | (shade_data_global == 1))
        if np.any(shade_mask_local) and np.any(shade_mask_global):
            y_true_shade = local_data_masked[shade_mask_local].flatten()
            y_pred_shade = global_data_masked[shade_mask_global].flatten()
            stats = compute_stats(y_true_shade, y_pred_shade)
            stats_results.append({'Time': time, 'Mask': 'Shade (Building and Tree)', **stats})
        else:
            print(f"⚠️  {time}: No shade pixels found")
        
        # no shade
        noshade_mask_local = mask & (shade_data_local == 2)
        noshade_mask_global = mask & (shade_data_global == 2)
        if np.any(noshade_mask_local) and np.any(noshade_mask_global):
            y_true_noshade = local_data_masked[noshade_mask_local].flatten()
            y_pred_noshade = global_data_masked[noshade_mask_global].flatten()
            stats = compute_stats(y_true_noshade, y_pred_noshade)
            stats_results.append({'Time': time, 'Mask': 'No Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'No Shade' pixels found")
        
        # building shade
        bldg_mask_local = mask & (shade_data_local == 0)
        bldg_mask_global = mask & (shade_data_global == 0)
        if np.any(bldg_mask_local) and np.any(bldg_mask_global):
            y_true_bldg = local_data_masked[bldg_mask_local].flatten()
            y_pred_bldg = global_data_masked[bldg_mask_global].flatten()
            stats = compute_stats(y_true_bldg, y_pred_bldg)
            stats_results.append({'Time': time, 'Mask': 'Building Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Building Shade' pixels found")
        
        # tree shade
        tree_mask_local = mask & (shade_data_local == 1)
        tree_mask_global = mask & (shade_data_global == 1)
        if np.any(tree_mask_local) and np.any(tree_mask_global):
            y_true_tree = local_data_masked[tree_mask_local].flatten()
            y_pred_tree = global_data_masked[tree_mask_global].flatten()
            stats = compute_stats(y_true_tree, y_pred_tree)
            stats_results.append({'Time': time, 'Mask': 'Tree Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Tree Shade' pixels found")
        
        # overlapping shade statistics
        shade_type_names = {0: 'Building Shade', 1: 'Tree Shade', 2: 'No Shade'}
        
        for i in range(3):
            class_mask_local = (shade_data_local == i) & mask
            class_mask_global = (shade_data_global == i) & mask
            combined_mask_shade = class_mask_local & class_mask_global
            
            if np.any(combined_mask_shade):
                local_values = local_data_masked[combined_mask_shade]
                global_values = global_data_masked[combined_mask_shade]

                differences = local_values - global_values
                non_zero_differences = differences[differences != 0]
                no_differences = len(differences[differences == 0])
                
                total_pixels = len(local_values)
                num_differences = len(non_zero_differences)
                percentage_differences = round((num_differences / total_pixels) * 100, 4)
                min_diff = round(np.min(differences), 4)
                median_diff = round(np.median(differences), 4)
                max_diff = round(np.max(differences), 4)
                std_diff = round(np.std(differences), 4)
                mean_diff = round(np.mean(differences), 4)
                
                total_local_shade_pixels = np.sum(class_mask_local)
                percentage_overlapping = round((combined_mask_shade.sum() / total_local_shade_pixels) * 100, 4)
                
                overlapping_shade_results.append({
                    'Time': time,
                    'Shade Type': shade_type_names[i],
                    'No Differences (number of pixels)': no_differences,
                    'Percentage Non-zero Differences (%)': percentage_differences,
                    'Percentage Overlapping (%)': percentage_overlapping,
                    'Mean Difference (local - global)': mean_diff,
                    'Min Difference (local - global)': min_diff,
                    'Median Difference (local - global)': median_diff,
                    'Max Difference (local - global)': max_diff,
                    'Std Difference': std_diff
                })
        overlapping_shade_df = pd.DataFrame(overlapping_shade_results)
        overlapping_shade_df.to_csv(output_dir / f"utci_overlapping_shade_{city}_{mask_name}.csv", index=False)
        print(f"✅ Overlapping shade results saved to {output_dir / f'utci_overlapping_shade_{city}_{mask_name}.csv'}")
    pd.DataFrame(stats_results).to_csv(output_dir / f"utci_stats_{city}_{mask_name}.csv", index=False)
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
    city_name = "RiodeJaneiro"
    config = {"city": city_name, **all_configs[city_name]}
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    shade_paths_local = config['shade_local_paths']
    shade_paths_global = config['shade_global_paths']

    # Check if local files exist, otherwise download from URL
    for local_path in local_utci_paths:
        if not file_exists_locally(local_path):
            url_key = f"url_{Path(local_path).name.replace('.tif', '')}"
            if url_key in config:
                download_from_url(config[url_key], local_path)
            else:
                print(f"⚠️  No URL found for {local_path}")
    
    for global_path in global_utci_paths:
        if not file_exists_locally(global_path):
            url_key = f"url_{Path(global_path).name.replace('.tif', '')}"
            if url_key in config:
                download_from_url(config[url_key], global_path)
            else:
                print(f"⚠️  No URL found for {global_path}")
    
    for shade_path in shade_paths_local + shade_paths_global:
        if not file_exists_locally(shade_path):
            url_key = f"url_{Path(shade_path).name.replace('.tif', '')}"
            if url_key in config:
                download_from_url(config[url_key], shade_path)
            else:
                print(f"⚠️  No URL found for {shade_path}")

    # check if any path contains '_20m'
    is_20m = any('_20m' in path for path in local_utci_paths + global_utci_paths)

    # set output directory
    output_dir_base = Path(f"results/utci/{city_name}/20m/metrics") if is_20m else Path(f"results/utci/{city_name}/metrics")
    output_dir_base.mkdir(parents=True, exist_ok=True)

    # Select mask paths as in shade_val_masks.py
    mask_paths = config.get('mask_paths', {})
    masks = {
        "pedestrian": mask_paths.get('pedestrian_mask_path'),
        "non_building": mask_paths.get('land_use_mask_path')
    }
    print(f"Starting UTCI validation for {city_name}")
    print(f"   Masks to validate: {list(masks.keys())}")
    for mask_name, mask_path in masks.items():
        if mask_path is None:
            print(f"⚠️  Skipping {mask_name} - no mask path provided")
            continue
        output_dir = output_dir_base.parent / mask_name / "metrics"
        output_dir.mkdir(parents=True, exist_ok=True)
        validate_utci_from_config(city_name, local_utci_paths, global_utci_paths, shade_paths_local, shade_paths_global, mask_path, mask_name, output_dir)
    print(f"\n✅ All UTCI validations completed for {city_name}")

if __name__ == "__main__":
    main() 




