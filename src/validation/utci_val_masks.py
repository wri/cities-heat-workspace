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

# mask specific 
def validate_utci_for_mask(city, local_utci_paths, global_utci_paths, shade_paths, mask_path, mask_name, output_dir):
    print(f"\n Validating UTCI for {city} - {mask_name}")
    
    # output_dir.mkdir(parents=True, exist_ok=True)
    
    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_utci_paths]
    stats_results = []
    
    # load mask 
    with rasterio.open(mask_path) as mask_src:
        mask_data = mask_src.read(1)
        mask_transform = mask_src.transform
        mask_bounds = mask_src.bounds
        mask_crs = mask_src.crs
    
    for time, local_path, global_path, shade_path in zip(base_time_steps, local_utci_paths, global_utci_paths, shade_paths):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global, rasterio.open(shade_path) as src_shade:
                print(f"[DEBUG] Local shape, bounds, transform: {src_local.shape}, {src_local.bounds}, {src_local.transform}")
                print(f"[DEBUG] Global shape, bounds, transform: {src_global.shape}, {src_global.bounds}, {src_global.transform}")
                print(f"[DEBUG] Shade shape, bounds, transform: {src_shade.shape}, {src_shade.bounds}, {src_shade.transform}")
                print(f"[DEBUG] Mask shape, bounds, transform: {mask_data.shape}, {mask_bounds}, {mask_transform}")
                
                # check if all rasters are aligned
                all_sources = [src_local, src_global, src_shade]
                all_aligned = all(
                    src.crs == mask_crs and
                    src.transform == mask_transform and
                    src.shape == mask_data.shape and
                    src.bounds == mask_bounds
                    for src in all_sources
                )
                
                if not all_aligned:
                    print(f"🟠 {time}: Raster mismatch with mask. Cropping to overlap and trimming boundary.")
                    # create temporary mask source for overlap calculation
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
        
        # classify shade data from raw values to class labels
        shade_data = classify_raster(raw_shade_data)
        
        # apply mask intersection (only analyze pixels where mask = 1)
        mask_valid = (mask_data_cropped == 1)
        
        # base valid mask for UTCI and shade data
        valid_mask = (~np.isnan(local_data)) & (~np.isnan(global_data)) & (shade_data != -1)
        
        # combined mask: valid data AND mask intersection
        combined_mask = valid_mask & mask_valid
        
        # show mask intersection statistics
        total_pixels = np.prod(mask_data_cropped.shape)
        mask_pixels = np.sum(mask_valid)
        valid_pixels = np.sum(valid_mask)
        combined_pixels = np.sum(combined_mask)
        
        print(f"[DEBUG] {time}: Total pixels: {total_pixels}")
        print(f"[DEBUG] {time}: Mask pixels (==1): {mask_pixels} ({mask_pixels/total_pixels*100:.1f}%)")
        print(f"[DEBUG] {time}: Valid UTCI+shade pixels: {valid_pixels} ({valid_pixels/total_pixels*100:.1f}%)")
        print(f"[DEBUG] {time}: Combined mask pixels: {combined_pixels} ({combined_pixels/total_pixels*100:.1f}%)")
        
        if combined_pixels == 0:
            print(f"⚠️  {time}: No valid pixels in mask intersection")
            continue
        
        # show shade data distribution within mask
        shade_in_mask = shade_data[combined_mask]
        unique_shade_values = np.unique(shade_in_mask)
        print(f"[DEBUG] {time}: Shade classes in mask: {unique_shade_values}")
        for shade_val in unique_shade_values:
            count = np.sum(shade_in_mask == shade_val)
            shade_name = {0: "Building Shade", 1: "Tree Shade", 2: "No Shade"}.get(shade_val, f"Unknown({shade_val})")
            print(f"[DEBUG] {time}: {shade_name}: {count} pixels ({count/len(shade_in_mask)*100:.1f}%)")
       
        # all area within mask
        y_true = local_data[combined_mask].flatten()
        y_pred = global_data[combined_mask].flatten()
        stats = compute_stats(y_true, y_pred)
        stats_results.append({'Time': time, 'Mask': 'Whole Area', **stats})
        
        # shade (building and tree) within mask
        shade_mask = combined_mask & ((shade_data == 0) | (shade_data == 1))
        if np.any(shade_mask):
            y_true_shade = local_data[shade_mask].flatten()
            y_pred_shade = global_data[shade_mask].flatten()
            stats = compute_stats(y_true_shade, y_pred_shade)
            stats_results.append({'Time': time, 'Mask': 'Shade (Building and Tree)', **stats})
        else:
            print(f"⚠️  {time}: No shade pixels found in mask")
       
        # no shade within mask
        noshade_mask = combined_mask & (shade_data == 2)
        if np.any(noshade_mask):
            y_true_noshade = local_data[noshade_mask].flatten()
            y_pred_noshade = global_data[noshade_mask].flatten()
            stats = compute_stats(y_true_noshade, y_pred_noshade)
            stats_results.append({'Time': time, 'Mask': 'No Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'No Shade' pixels found in mask")
        
        # building shade within mask
        bldg_mask = combined_mask & (shade_data == 0)
        if np.any(bldg_mask):
            y_true_bldg = local_data[bldg_mask].flatten()
            y_pred_bldg = global_data[bldg_mask].flatten()
            stats = compute_stats(y_true_bldg, y_pred_bldg)
            stats_results.append({'Time': time, 'Mask': 'Building Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Building Shade' pixels found in mask")
        
        # tree shade within mask
        tree_mask = combined_mask & (shade_data == 1)
        if np.any(tree_mask):
            y_true_tree = local_data[tree_mask].flatten()
            y_pred_tree = global_data[tree_mask].flatten()
            stats = compute_stats(y_true_tree, y_pred_tree)
            stats_results.append({'Time': time, 'Mask': 'Tree Shade', **stats})
        else:
            print(f"⚠️  {time}: No 'Tree Shade' pixels found in mask")
    
    # save results with mask suffix
    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    output_file = output_dir / f"utci_stats_{city}{mask_suffix}.csv"
    pd.DataFrame(stats_results).to_csv(output_file, index=False)
    print(f"✅ UTCI validation complete for {city} - {mask_name}. Results saved to {output_file}")

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    
    city_name = "Monterrey1"
    config = {"city": city_name, **all_configs[city_name]}
    
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    shade_paths = config['shade_local_paths']  # Use local shade classification for masking
    
    masks = {
        "pedestrian": config.get('mask_paths', {}).get('pedestrian_mask_path'),
        "non_building": config.get('mask_paths', {}).get('land_use_mask_path')
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