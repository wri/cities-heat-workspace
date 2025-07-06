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

def classify_raster(data):
    shade_classes = {0.00: 0, 0.03: 1, 1.00: 2}
    classified = np.full(data.shape, -1, dtype=np.int8)
    for val, label in shade_classes.items():
        mask = np.isclose(data, val, atol=0.0005)
        classified[mask] = label
    return classified

def get_overlap_window(srcs):
    # Accepts a list of rasterio datasets, returns a window for each cropped to the overlap
    bounds = [s.bounds for s in srcs]
    crs = srcs[0].crs
    # Transform all bounds to the first raster's CRS if needed
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
        'MAE': mean_absolute_error(y_true, y_pred),
        'R2': r2_score(y_true, y_pred),
        'Min True': np.min(y_true),
        'Max True': np.max(y_true),
        'Mean True': np.mean(y_true),
        'Median True': np.median(y_true),
        'Std True': np.std(y_true),
        'Min Pred': np.min(y_pred),
        'Max Pred': np.max(y_pred),
        'Mean Pred': np.mean(y_pred),
        'Median Pred': np.median(y_pred),
        'Std Pred': np.std(y_pred)
    }

def validate_utci_from_config(config):
    city = config['city']
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    shade_paths = config['shade_local_paths']  # Use local shade classification for masking
    output_dir = Path(f"results/utci/{city}/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_utci_paths]
    stats_results = []
    
    for time, local_path, global_path, shade_path in zip(base_time_steps, local_utci_paths, global_utci_paths, shade_paths):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global, rasterio.open(shade_path) as src_shade:
                print(f"[DEBUG] Local shape, bounds, transform: {src_local.shape}, {src_local.bounds}, {src_local.transform}")
                print(f"[DEBUG] Global shape, bounds, transform: {src_global.shape}, {src_global.bounds}, {src_global.transform}")
                print(f"[DEBUG] Shade shape, bounds, transform: {src_shade.shape}, {src_shade.bounds}, {src_shade.transform}")
                
                aligned = (
                    src_local.crs == src_global.crs == src_shade.crs and
                    src_local.transform == src_global.transform == src_shade.transform and
                    src_local.shape == src_global.shape == src_shade.shape and
                    src_local.bounds == src_global.bounds == src_shade.bounds
                )
                
                if not aligned:
                    print(f"🟠 {time}: Raster mismatch. Cropping to overlap and trimming boundary.")
                    win_local, win_global, win_shade = get_overlap_window([src_local, src_global, src_shade])
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    win_shade = shrink_window(win_shade, 10)
                    local_data = src_local.read(1, window=win_local)
                    global_data = src_global.read(1, window=win_global)
                    raw_shade_data = src_shade.read(1, window=win_shade)
                else:
                    print(f"🟢 {time}: Rasters aligned. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local_data = src_local.read(1, window=window)
                    global_data = src_global.read(1, window=window)
                    raw_shade_data = src_shade.read(1, window=window)
        
        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue
        
        # Classify shade data from raw values to class labels
        shade_data = classify_raster(raw_shade_data)
        
        # Mask for valid data
        valid_mask = (~np.isnan(local_data)) & (~np.isnan(global_data)) & (shade_data != -1)
        
        # Debug: Show shade data distribution
        unique_raw_values = np.unique(raw_shade_data[~np.isnan(raw_shade_data)])
        unique_classified_values = np.unique(shade_data[shade_data != -1])
        print(f"[DEBUG] {time}: Raw shade values: {unique_raw_values}")
        print(f"[DEBUG] {time}: Classified shade values: {unique_classified_values}")
        print(f"[DEBUG] {time}: Valid pixels %: {np.sum(valid_mask)/np.sum(~np.isnan(local_data))*100}")
       
        # All area
        y_true = local_data[valid_mask].flatten()
        y_pred = global_data[valid_mask].flatten()
        stats = compute_stats(y_true, y_pred)
        stats_results.append({'Time': time, 'Mask': 'Whole Area', **stats})
        
        # Shade (building and tree)
        shade_mask = valid_mask & ((shade_data == 0) | (shade_data == 1))
        if np.any(shade_mask):
            y_true_shade = local_data[shade_mask].flatten()
            y_pred_shade = global_data[shade_mask].flatten()
            stats = compute_stats(y_true_shade, y_pred_shade)
            stats_results.append({'Time': time, 'Mask': 'Shade (Building and Tree)', **stats})
        else:
            print(f"⚠️  {time}: No shade pixels found")
       
        # No shade
        noshade_mask = valid_mask & (shade_data == 2)
        if np.any(noshade_mask):
            y_true_noshade = local_data[noshade_mask].flatten()
            y_pred_noshade = global_data[noshade_mask].flatten()
            stats = compute_stats(y_true_noshade, y_pred_noshade)
            stats_results.append({'Time': time, 'Mask': 'No Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'No Shade' pixels found")
        
        # Building shade
        bldg_mask = valid_mask & (shade_data == 0)
        if np.any(bldg_mask):
            y_true_bldg = local_data[bldg_mask].flatten()
            y_pred_bldg = global_data[bldg_mask].flatten()
            stats = compute_stats(y_true_bldg, y_pred_bldg)
            stats_results.append({'Time': time, 'Mask': 'Building Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Building Shade' pixels found")
        
        # Tree shade
        tree_mask = valid_mask & (shade_data == 1)
        if np.any(tree_mask):
            y_true_tree = local_data[tree_mask].flatten()
            y_pred_tree = global_data[tree_mask].flatten()
            stats = compute_stats(y_true_tree, y_pred_tree)
            stats_results.append({'Time': time, 'Mask': 'Tree Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Tree Shade' pixels found")
    
    pd.DataFrame(stats_results).to_csv(output_dir / f"utci_stats_{city}.csv", index=False)
    print(f"✅ UTCI validation complete for {city}. Results saved to {output_dir.resolve()}")

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    
    city_name = "RiodeJaneiro"
    config = {"city": city_name, **all_configs[city_name]}
    validate_utci_from_config(config)

if __name__ == "__main__":
    main() 