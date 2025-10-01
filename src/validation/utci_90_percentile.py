import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
import yaml
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
"""
1) for each city, for each time stamp, calculate absolute error for each pixel and save as a numpy array
2) calculate 90th and 95th percentile of the absolute error for each city and save per-city results
3) concatenate arrays of each timestamp across different cities and calculate aggregate 90th and 95th percentile
4) save both per-city and aggregate results as csv files
❗️ This does not take into account the different shade clusters. e.g. a pixel could be classified as "building" in local but "tree" in global. 
It's rather a global performance summary

Per-city results saved to: results/utci/{city_name}/metrics/utci_percentiles_{city_name}.csv
Aggregate results saved to: results/utci/percentile/metrics/utci_all_percentiles.csv
"""


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

# def compute_stats(y_true, y_pred):
#     return {
#         # 'MAE': round(mean_absolute_error(y_true, y_pred), 4),
#         # 'R2': round(r2_score(y_true, y_pred), 4),
#         'Mean Error (global - local)': round(round(np.mean(y_pred), 4) - round(np.mean(y_true), 4), 4),
#         'Min True (local)': round(np.min(y_true), 4),
#         'Max True (local)': round(np.max(y_true), 4),
#         'Mean True (local)': round(np.mean(y_true), 4),
#         'Median True (local)': round(np.median(y_true), 4),
#         'Std True (local)': round(np.std(y_true), 4),
#         'Min Pred (global)': round(np.min(y_pred), 4),
#         'Max Pred (global)': round(np.max(y_pred), 4),
#         'Mean Pred (global)': round(np.mean(y_pred), 4),
#         'Median Pred (global)': round(np.median(y_pred), 4),
#         'Std Pred (global)': round(np.std(y_pred), 4)
#     }

def validate_utci_from_config(city, local_utci_paths, global_utci_paths, all_absolute_errors_by_time, city_errors_by_time):
    print(f"Validating UTCI for {city}")
    
    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_utci_paths]
    
    for time, local_path, global_path in zip(base_time_steps, local_utci_paths, global_utci_paths):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global:
                print(f"[DEBUG] Local shape, bounds, transform: {src_local.shape}, {src_local.bounds}, {src_local.transform}")
                print(f"[DEBUG] Global shape, bounds, transform: {src_global.shape}, {src_global.bounds}, {src_global.transform}")

                aligned = (
                    src_local.crs == src_global.crs and
                    src_local.transform == src_global.transform   and
                    src_local.shape == src_global.shape   and
                    src_local.bounds == src_global.bounds 
                )
                
                if not aligned:
                    print(f"🟠 {time}: Raster mismatch. Cropping to overlap and trimming boundary.")
                    win_local, win_global = get_overlap_window([src_local, src_global])
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    local_data = src_local.read(1, window=win_local)
                    global_data = src_global.read(1, window=win_global)
                else:
                    print(f"🟢 {time}: Rasters aligned. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local_data = src_local.read(1, window=window)
                    global_data = src_global.read(1, window=window)

        
        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue
        

        # mask for valid data (valid in pixel)
        valid_mask = (~np.isnan(local_data)) & (~np.isnan(global_data))

       
        # all area 
        y_true = local_data[valid_mask].flatten()
        y_pred = global_data[valid_mask].flatten()

        # absolute error per timestamp
        abs_errors = np.abs(y_true - y_pred)

        # store for aggregate results (all cities combined)
        if time not in all_absolute_errors_by_time:
            all_absolute_errors_by_time[time] = []
        all_absolute_errors_by_time[time].append(abs_errors)

        # store for per-city results
        if time not in city_errors_by_time:
            city_errors_by_time[time] = []
        city_errors_by_time[time].append(abs_errors)
    


def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    # set output directory for aggregate results
    aggregate_output_dir = Path("results/utci/percentile/metrics")
    aggregate_output_dir.mkdir(parents=True, exist_ok=True)
    all_absolute_errors_by_time = {}

    for city_name, city_config in all_configs.items():
        print(f"\n======= Processing {city_name}========")

        required_keys = {'utci_local_paths','utci_global_paths'}
        if not all(k in city_config for k in required_keys):
            print(f"⚠️ Skipping {city_name}: incomplete configuration file.")
            continue

        # select paths
        local_utci_paths = city_config['utci_local_paths']
        global_utci_paths = city_config['utci_global_paths']

        # create per-city error dictionary
        city_errors_by_time = {}

        # validate and collect errors
        validate_utci_from_config(city_name, local_utci_paths, global_utci_paths, all_absolute_errors_by_time, city_errors_by_time)

        # compute and save per-city percentiles
        if city_errors_by_time:
            city_records = []
            for time_step, errors_list in city_errors_by_time.items():
                errors = np.concatenate(errors_list)
                record = {        
                    'Time': time_step,
                    'Mean Absolute Error': round(np.mean(errors), 4),
                    'Minimum Absolute Error': round(np.min(errors), 4),
                    'Maximum Absolute Error': round(np.max(errors), 4),
                    '90th percentile': round(np.percentile(errors, 90), 4),
                    '95th percentile': round(np.percentile(errors, 95), 4)
                }
                city_records.append(record)

            # save per-city results
            city_output_dir = Path(f"results/utci/{city_name}/metrics")
            city_output_dir.mkdir(parents=True, exist_ok=True)
            city_df = pd.DataFrame(city_records)
            city_df.to_csv(city_output_dir / f"utci_percentiles_{city_name}.csv", index=False)
            print(f"✅ Saved per-city percentiles to {city_output_dir / f'utci_percentiles_{city_name}.csv'}")

    # compute and save aggregate percentiles after all cities are run
    print("\n======= Computing aggregate absolute error percentiles across all cities =======")
    
    records = []
    for time_step, errors_list in all_absolute_errors_by_time.items():
        errors = np.concatenate(errors_list)
        record = {        
            'Time': time_step,
            'Mean Absolute Error': round(np.mean(errors), 4),
            'Minimum Absolute Error': round(np.min(errors), 4),
            'Maximum Absolute Error': round(np.max(errors), 4),
            '90th percentile': round(np.percentile(errors, 90), 4),
            '95th percentile': round(np.percentile(errors, 95), 4)
        }
        records.append(record)

    summary_df = pd.DataFrame(records)
    summary_df.to_csv(aggregate_output_dir / "utci_all_percentiles.csv", index=False)
    print(f"✅ Saved aggregate percentiles to {aggregate_output_dir / 'utci_all_percentiles.csv'}")

    
    print("\n ✅ All cities processed and percentiles metrics saved.")


if __name__ == "__main__":
    main() 




