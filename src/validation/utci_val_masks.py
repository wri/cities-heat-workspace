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

# mask specific 
def validate_utci_for_mask(city, local_utci_paths, global_utci_paths, shade_paths, mask_path, mask_name, output_dir):
    print(f"\n Validating UTCI for {city} - {mask_name}")
    
    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_utci_paths]
    stats_results = []
    overlapping_shade_results = []  # For overlapping shade statistics
    
    with rasterio.open(mask_path) as mask_src:
        mask_data = mask_src.read(1)
        mask_transform = mask_src.transform
        mask_bounds = mask_src.bounds
        mask_crs = mask_src.crs
    
    for time, local_path, global_path, shade_path in zip(base_time_steps, local_utci_paths, global_utci_paths, shade_paths):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global, rasterio.open(shade_path) as src_shade:
                aligned = (
                    src_local.crs == src_global.crs == src_shade.crs == mask_crs and
                    src_local.transform == src_global.transform == src_shade.transform == mask_transform and
                    src_local.shape == src_global.shape == src_shade.shape == mask_data.shape and
                    src_local.bounds == src_global.bounds == src_shade.bounds == mask_bounds
                )
                
                if not aligned:
                    print(f"🟠 {time}: Raster mismatch with mask. Cropping to overlap and trimming boundary.")
                    from rasterio.io import MemoryFile
                    with MemoryFile() as memfile:
                        with memfile.open(
                            driver='GTiff',
                            height=mask_data.shape[0],
                            width=mask_data.shape[1],
                            count=1,
                            dtype=mask_data.dtype,
                            crs=mask_crs,
                            transform=mask_transform,
                        ) as temp_mask:
                            temp_mask.write(mask_data, 1)
                            
                            win_local, win_global, win_shade, win_mask = get_overlap_window([src_local, src_global, src_shade, temp_mask])
                            win_local = shrink_window(win_local, 10)
                            win_global = shrink_window(win_global, 10)
                            win_shade = shrink_window(win_shade, 10)
                            win_mask = shrink_window(win_mask, 10)
                            
                            local_data = src_local.read(1, window=win_local)
                            global_data = src_global.read(1, window=win_global)
                            raw_shade_data = src_shade.read(1, window=win_shade)
                            mask_data_cropped = temp_mask.read(1, window=win_mask)
                else:
                    print(f"🟢 {time}: All rasters aligned with mask. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local_data = src_local.read(1, window=window)
                    global_data = src_global.read(1, window=window)
                    raw_shade_data = src_shade.read(1, window=window)
                    mask_data_cropped = mask_data[window.row_off:window.row_off+window.height, 
                                                 window.col_off:window.col_off+window.width]
        
        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue
        
        shade_data = classify_raster(raw_shade_data)
        mask_valid = (mask_data_cropped == 1)
        valid_mask = (~np.isnan(local_data)) & (~np.isnan(global_data)) & (shade_data != -1)
        combined_mask = valid_mask & mask_valid
        
        if np.sum(combined_mask) == 0:
            print(f"⚠️  {time}: No valid pixels in mask intersection")
            continue
        
        # Compute statistics for the whole area within the mask
        y_true = local_data[combined_mask].flatten()
        y_pred = global_data[combined_mask].flatten()
        stats = compute_stats(y_true, y_pred)
        stats_results.append({'Time': time, 'Mask': 'Whole Area', **stats})
        
        # Compute statistics for each shade type within the mask
        for shade_type, shade_name in {0: "Building Shade", 1: "Tree Shade", 2: "No Shade"}.items():
            shade_mask = combined_mask & (shade_data == shade_type)
            if np.any(shade_mask):
                y_true_shade = local_data[shade_mask].flatten()
                y_pred_shade = global_data[shade_mask].flatten()
                stats = compute_stats(y_true_shade, y_pred_shade)
                stats_results.append({'Time': time, 'Mask': shade_name, **stats})
            else:
                print(f"⚠️  {time}: No '{shade_name}' pixels found in mask")
        
        # Overlapping shade statistics
        for i in range(3):  # local and global shade classes: 0, 1, 2
            class_mask_local = (shade_data == i) & combined_mask
            class_mask_global = (shade_data == i) & combined_mask
            combined_mask_shade = class_mask_local & class_mask_global
            
            if np.any(combined_mask_shade):
                local_values = local_data[combined_mask_shade]
                global_values = global_data[combined_mask_shade]
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
                
                total_local_shade_pixels = np.sum(class_mask_local)
                percentage_overlapping = round((combined_mask_shade.sum() / total_local_shade_pixels) * 100, 4)
                
                overlapping_shade_results.append({
                    'Shade Type': {0: 'Building Shade', 1: 'Tree Shade', 2: 'No Shade'}[i],
                    'No Differences (number of pixels)': no_differences,
                    'Percentage Non-zero Differences (%)': percentage_differences,
                    # 'Percentage Overlapping (%)': percentage_overlapping,
                    'Min Difference (local - global)': min_diff,
                    'Median Difference (local - global)': median_diff,
                    'Max Difference (local - global)': max_diff,
                    'Std Difference': std_diff
                })
    
    # Save results
    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    output_file = output_dir / f"utci_stats_{city}{mask_suffix}.csv"
    pd.DataFrame(stats_results).to_csv(output_file, index=False)
    print(f"✅ UTCI validation complete for {city} - {mask_name}. Results saved to {output_file}")
    
    # Save overlapping shade results
    overlapping_shade_df = pd.DataFrame(overlapping_shade_results)
    overlapping_shade_df.to_csv(output_dir / f"utci_overlapping_shade_{city}{mask_suffix}.csv", index=False)
    print(f"✅ Overlapping shade results saved to {output_dir / f'utci_overlapping_shade_{city}{mask_suffix}.csv'}")

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    
    city_name = "Monterrey1"
    config = {"city": city_name, **all_configs[city_name]}
    
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    shade_paths = config['shade_local_paths']  # use local shade classification for masking
    
    masks = {
        "pedestrian": config.get('mask_paths', {}).get('pedestrian_mask_path'),
        # "non_building": config.get('mask_paths', {}).get('land_use_mask_path')
    }
    
    print(f"Starting UTCI validation for {city_name}")
    print(f"   Masks to validate: {list(masks.keys())}")
    
    for mask_name, mask_path in masks.items():
        if mask_path is None:
            print(f"⚠️  Skipping {mask_name} - no mask path provided")
            continue
        
        output_dir = Path(f"results/utci/{city_name}/{mask_name}/metrics")
        output_dir.mkdir(parents=True, exist_ok=True)
        validate_utci_for_mask(city_name, local_utci_paths, global_utci_paths, shade_paths, mask_path, mask_name, output_dir)
    
    print(f"\n✅ All UTCI validations completed for {city_name}")

if __name__ == "__main__":
    main() 