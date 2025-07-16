import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import numpy as np
import yaml
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds

# sample pixel numbers for scatter plots
SAMPLE_SIZE = 30000
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

MASK_LABELS = {
    'All': lambda shade: np.ones_like(shade, dtype=bool),
    'Shade': lambda shade: (shade == 0) | (shade == 1),
    'NoShade': lambda shade: (shade == 2),
    'BuildingShade': lambda shade: (shade == 0),
    'TreeShade': lambda shade: (shade == 1),
}

def classify_raster(data):
    shade_classes = {0.00: 0, 0.03: 1, 1.00: 2}
    classified = np.full(data.shape, -1, dtype=np.int8)
    for val, label in shade_classes.items():
        mask = np.isclose(data, val, atol=0.0005)
        classified[mask] = label
    return classified

def get_overlap_window(srcs):
    bounds = [s.bounds for s in srcs]
    crs = srcs[0].crs
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

def sample_df(df, n=SAMPLE_SIZE):
    return df.sample(n=n, random_state=RANDOM_SEED) if len(df) > n else df

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

def ensure_local_path(path, url):
    if not file_exists_locally(path):
        download_from_url(url, path)
    return path

# scatter plots for each timestamp
def plot_utci_pixel_scatter(local_utci_paths, global_utci_paths, shade_local_paths, shade_global_paths, output_dir, city_name, config):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    time_steps = [Path(p).stem.split('_')[-1] for p in local_utci_paths]
    
    # store processed data for each timestamp
    all_data = {}
    
    for t, local_path, global_path, shade_path_local, shade_path_global in zip(time_steps, local_utci_paths, global_utci_paths, shade_local_paths, shade_global_paths):
        print(f"Processing {t}: {local_path} vs {global_path}")
        
        try:
            local_path = ensure_local_path(local_path, config['utci_local_paths'])
            global_path = ensure_local_path(global_path, config['utci_global_paths'])
            shade_path_local = ensure_local_path(shade_path_local, config['shade_local_paths'])
            shade_path_global = ensure_local_path(shade_path_global, config['shade_global_paths'])
            
            # check data alignment
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global, rasterio.open(shade_path_local) as src_shade_local, rasterio.open(shade_path_global) as src_shade_global:
                aligned = (
                    src_local.crs == src_global.crs == src_shade_local.crs == src_shade_global.crs and
                    src_local.transform == src_global.transform == src_shade_local.transform == src_shade_global.transform and
                    src_local.shape == src_global.shape == src_shade_local.shape == src_shade_global.shape and
                    src_local.bounds == src_global.bounds == src_shade_local.bounds == src_shade_global.bounds
                )
                
                if not aligned:
                    print(f"🟠 {t}: Raster mismatch. Cropping to overlap and trimming boundary.")
                    win_local, win_global, win_shade_local, win_shade_global = get_overlap_window([src_local, src_global, src_shade_local, src_shade_global])
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    win_shade_local = shrink_window(win_shade_local, 10)
                    win_shade_global = shrink_window(win_shade_global, 10)
                    local = src_local.read(1, window=win_local)
                    global_ = src_global.read(1, window=win_global)
                    raw_shade_local = src_shade_local.read(1, window=win_shade_local)
                    raw_shade_global = src_shade_global.read(1, window=win_shade_global)
                else:
                    print(f"🟢 {t}: Rasters aligned. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local = src_local.read(1, window=window)
                    global_ = src_global.read(1, window=window)
                    raw_shade_local = src_shade_local.read(1, window=window)
                    raw_shade_global = src_shade_global.read(1, window=window)
        
        except Exception as e:
            print(f"❌ Error reading files for {t}: {e}")
            continue
        
        # classify shade data
        shade_local = classify_raster(raw_shade_local)
        shade_global = classify_raster(raw_shade_global)
        
        # store data for each mask type
        all_data[t] = {}
        for mask_name, mask_func in MASK_LABELS.items():
            # Create a combined mask for overlapping shade types
            overlap_mask = (shade_local == shade_global) & mask_func(shade_local) & mask_func(shade_global)
            
            valid_local = (~np.isnan(local)) & overlap_mask
            valid_global = (~np.isnan(global_)) & overlap_mask
            
            if np.sum(valid_local) == 0 or np.sum(valid_global) == 0:
                continue
                
            y_true_local = local[valid_local].flatten()
            y_pred_global = global_[valid_global].flatten()
            
            n = min(SAMPLE_SIZE, len(y_true_local), len(y_pred_global))
            
            if n < 2:
                continue
                
            np.random.seed(42)  # use same seed number
            idx_local = np.random.choice(len(y_true_local), n, replace=False)
            idx_global = np.random.choice(len(y_pred_global), n, replace=False)
            
            y_true_sample_local = y_true_local[idx_local]
            y_pred_sample_global = y_pred_global[idx_global]
            
            all_data[t][mask_name] = {
                'local': y_true_sample_local,
                'global': y_pred_sample_global
            }
    
    # determine consistent axis ranges for each timestamp (x and y axes)
    axis_ranges = {}
    for t in time_steps:
        all_local = []
        all_global = []
        if t in all_data:
            for mask_name, data in all_data[t].items():
                all_local.extend(data['local'])
                all_global.extend(data['global'])
        
        if all_local and all_global:
            min_val = min(min(all_local), min(all_global))
            max_val = max(max(all_local), max(all_global))
            axis_ranges[t] = (min_val, max_val)
    
    # create 3x1 subplot for each mask type
    for mask_name in MASK_LABELS.keys():
        timestamps_with_data = [t for t in time_steps if t in all_data and mask_name in all_data[t]]
        
        if not timestamps_with_data:
            continue
            
        fig, axes = plt.subplots(1, len(timestamps_with_data), figsize=(6*len(timestamps_with_data), 6))
        if len(timestamps_with_data) == 1:
            axes = [axes]
        
        for i, t in enumerate(timestamps_with_data):
            data = all_data[t][mask_name]
            y_true_sample_local = data['local']
            y_pred_sample_global = data['global']
            
            # create scatter plot with different colors for local and global
            axes[i].scatter(y_true_sample_local, y_pred_sample_global, alpha=0.4, s=1, color='purple', label='Local vs Global')

            min_val, max_val = axis_ranges[t]
            axes[i].plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='1:1 line')
            
            # # Add best fit line
            # reg = LinearRegression()
            # X_reg = y_true_sample_local.reshape(-1, 1)
            # reg.fit(X_reg, y_pred_sample_global)
            
            # X_line = np.linspace(min_val, max_val, 100).reshape(-1, 1)
            # y_line = reg.predict(X_line)
            
            # axes[i].plot(X_line, y_line, color='red', linewidth=2, label='Best fit')
            
            axes[i].set_xlabel('Local UTCI (°C)')
            axes[i].set_ylabel('Global UTCI (°C)')
            axes[i].set_title(f'{t}')
            axes[i].grid(True, alpha=0.3)
            axes[i].legend()
            
            # # Set consistent axis limits for this timestamp
            # axes[i].set_xlim(min_val, max_val)
            # axes[i].set_ylim(min_val, max_val)
            # axes[i].set_aspect('equal', adjustable='box')
        
        # Update title to include mask name
        fig.suptitle(f'{city_name}: UTCI {mask_name}', fontsize=16)
        plt.tight_layout()
        
        # Save the combined plot
        output_path = output_dir / f"utci_pixel_scatter_{mask_name}_combined.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {output_path}")

def plot_utci_lines(metrics_csv, output_dir, city_name):
    """Generate line plots from CSV metrics"""
    df = pd.read_csv(metrics_csv)
    masks = df['Mask'].unique()

    for mask in masks:
        subset = df[df['Mask'] == mask]
        if subset.empty:
            continue

        plt.figure(figsize=(8, 6))
        
        # Plot mean lines
        plt.plot(subset['Time'], subset['Mean True (local)'], marker='o', label='Local', color='blue', linewidth=2)
        plt.plot(subset['Time'], subset['Mean Pred (global)'], marker='o', label='Global', color='orange', linewidth=2)
        
        # Add standard deviation bands for Local (True) data
        plt.fill_between(subset['Time'], 
                        subset['Mean True (local)'] - subset['Std True (local)'], 
                        subset['Mean True (local)'] + subset['Std True (local)'], 
                        color='blue', alpha=0.2, label='Local ± Std')
        
        # Add standard deviation bands for Global (Pred) data
        plt.fill_between(subset['Time'], 
                        subset['Mean Pred (global)'] - subset['Std Pred (global)'], 
                        subset['Mean Pred (global)'] + subset['Std Pred (global)'], 
                        color='orange', alpha=0.2, label='Global ± Std')
        
        # # Keep the bias region between means
        # plt.fill_between(subset['Time'], subset['Mean True'], subset['Mean Pred'],
        #                  color='gray', alpha=0.15, label='Bias Region')

        plt.xlabel('Time')
        plt.ylabel('Mean UTCI (°C)')
        plt.title(f'{city_name}: Mean UTCI by Time - {mask}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        out_path = Path(output_dir) / f'utci_line_mean_{mask}.png'
        plt.savefig(out_path, dpi=300)
        plt.close()

# error line plots
# def plot_utci_error_lines(metrics_csv, output_dir, city_name):

#     df = pd.read_csv(metrics_csv)
#     masks = df['Mask'].unique()

#     for mask in masks:
#         subset = df[df['Mask'] == mask]
#         if subset.empty:
#             continue

#         plt.figure(figsize=(5, 5))
#         plt.plot(subset['Time'], subset['MAE'], marker='o', color='crimson', label='MAE')
#         subset = subset.copy()
#         subset['Signed Error'] = subset['Mean Pred (global)'] - subset['Mean True (local)']
#         plt.plot(subset['Time'], subset['Signed Error'], marker='s', color='green', label='Signed Error')

#         plt.xlabel('Time')
#         plt.ylabel('UTCI Error (°C)')
#         plt.title(f'{city_name}: UTCI Error over Time - {mask}')
#         plt.axhline(0, linestyle='--', color='gray')
#         plt.legend()
#         plt.tight_layout()
#         out_path = Path(output_dir) / f'utci_error_line_{mask}.png'
#         plt.savefig(out_path, dpi=300)
#         plt.close()

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    # ‼️ change the city name here based on the city name in city_config.yaml
    city_name = "Monterrey1"
    config = {"city": city_name, **all_configs[city_name]}

    # file paths
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    
    # add local and global shade paths
    shade_local_paths = config['shade_local_paths']
    shade_global_paths = config['shade_global_paths']  
    
    metrics_csv = f"results/utci/{city_name}/metrics/utci_stats_{city_name}.csv"
    output_dir = Path(f"results/utci/{city_name}/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # generate all plots
    plot_utci_pixel_scatter(local_utci_paths, global_utci_paths, shade_local_paths, shade_global_paths, output_dir, city_name, config)
    plot_utci_lines(metrics_csv, output_dir, city_name)
    # plot_utci_error_lines(metrics_csv, output_dir, city_name)

    print("✅ All UTCI plots generated.")

if __name__ == "__main__":
    main() 