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

# def plot_utci_scatter_from_csv(metrics_csv, output_dir, city_name):
#     """Generate scatter plots from CSV metrics (aggregated data)"""
#     df = pd.read_csv(metrics_csv)
#     masks = df['Mask'].unique()
#     times = df['Time'].unique()

#     for mask in masks:
#         for t in times:
#             subset = df[(df['Mask'] == mask) & (df['Time'] == t)]
#             if subset.empty:
#                 continue
#             subset = sample_df(subset)

#             plt.figure(figsize=(6, 6))
#             sns.kdeplot(x=subset['Mean True'], y=subset['Mean Pred'], fill=True, cmap="Blues", thresh=0.05)
#             plt.scatter(subset['Mean True'], subset['Mean Pred'], s=10, alpha=0.3, color='black', label='Samples')

#             if len(subset) > 1:
#                 X = subset['Mean True'].values.reshape(-1, 1)
#                 y = subset['Mean Pred'].values
#                 model = LinearRegression().fit(X, y)
#                 y_pred = model.predict(X)

#                 r2 = r2_score(y, y_pred)
#                 mae = mean_absolute_error(y, y_pred)
#                 rmse = np.sqrt(mean_squared_error(y, y_pred))

#                 plt.plot(X, y_pred, color='red', label='Best fit')
#                 plt.plot([X.min(), X.max()], [X.min(), X.max()], 'k--', label='1:1 line')
#                 plt.text(0.05, 0.95, f"$R^2$={r2:.2f}\nMAE={mae:.2f}\nRMSE={rmse:.2f}",
#                          transform=plt.gca().transAxes, va='top', fontsize=9)

#             plt.xlabel('Mean UTCI (Local)')
#             plt.ylabel('Mean UTCI (Global)')
#             plt.title(f'{city_name} {t}: UTCI Scatter - {mask}')
#             plt.legend()
#             plt.tight_layout()
#             out_path = Path(output_dir) / f'utci_scatter_{mask}_{t}.png'
#             plt.savefig(out_path, dpi=300)
#             plt.close()

# scatter plots for each timestamp
def plot_utci_pixel_scatter(local_utci_paths, global_utci_paths, shade_paths, output_dir, city_name):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    time_steps = [Path(p).stem.split('_')[-1] for p in local_utci_paths]
    
    # First pass: collect all data to determine consistent axis ranges for each timestamp
    all_data = {}
    
    for t, local_path, global_path, shade_path in zip(time_steps, local_utci_paths, global_utci_paths, shade_paths):
        print(f"Processing {t}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global, rasterio.open(shade_path) as src_shade:
                aligned = (
                    src_local.crs == src_global.crs == src_shade.crs and
                    src_local.transform == src_global.transform == src_shade.transform and
                    src_local.shape == src_global.shape == src_shade.shape and
                    src_local.bounds == src_global.bounds == src_shade.bounds
                )
                
                if not aligned:
                    print(f"🟠 {t}: Raster mismatch. Cropping to overlap and trimming boundary.")
                    win_local, win_global, win_shade = get_overlap_window([src_local, src_global, src_shade])
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    win_shade = shrink_window(win_shade, 10)
                    local = src_local.read(1, window=win_local)
                    global_ = src_global.read(1, window=win_global)
                    raw_shade = src_shade.read(1, window=win_shade)
                else:
                    print(f"🟢 {t}: Rasters aligned. Trimming boundary.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    local = src_local.read(1, window=window)
                    global_ = src_global.read(1, window=window)
                    raw_shade = src_shade.read(1, window=window)
        
        except Exception as e:
            print(f"❌ Error reading files for {t}: {e}")
            continue
        
        # Classify shade data
        shade = classify_raster(raw_shade)
        
        # Store data for each mask type
        all_data[t] = {}
        for mask_name, mask_func in MASK_LABELS.items():
            valid = (~np.isnan(local)) & (~np.isnan(global_)) & (shade != -1)
            mask = valid & mask_func(shade)
            
            if np.sum(mask) == 0:
                continue
                
            y_true = local[mask].flatten()
            y_pred = global_[mask].flatten()
            n = min(SAMPLE_SIZE, len(y_true))
            
            if n < 2:
                continue
                
            np.random.seed(42)  # For reproducibility
            idx = np.random.choice(len(y_true), n, replace=False)
            y_true_sample = y_true[idx]
            y_pred_sample = y_pred[idx]
            
            all_data[t][mask_name] = {
                'local': y_true_sample,
                'global': y_pred_sample
            }
    
    # Determine consistent axis ranges for each timestamp (across all mask types)
    axis_ranges = {}
    for t in time_steps:
        if t not in all_data:
            continue
        all_local = []
        all_global = []
        for mask_name, data in all_data[t].items():
            all_local.extend(data['local'])
            all_global.extend(data['global'])
        
        if all_local and all_global:
            min_val = min(min(all_local), min(all_global))
            max_val = max(max(all_local), max(all_global))
            axis_ranges[t] = (min_val, max_val)
    
    # Create individual scatter plots for each timestamp and mask combination
    for mask_name in MASK_LABELS.keys():
        for t in time_steps:
            if t not in all_data or mask_name not in all_data[t]:
                continue
                
            data = all_data[t][mask_name]
            y_true_sample = data['local']
            y_pred_sample = data['global']
            
            fig, ax = plt.subplots(figsize=(8, 8))
            
            # Create scatter plot
            ax.scatter(y_true_sample, y_pred_sample, alpha=0.6, s=1, color='#1f77b4')
            
            # Add 1:1 line
            min_val, max_val = axis_ranges[t]
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='1:1 line')
            
            # Add best fit line
            from sklearn.linear_model import LinearRegression
            reg = LinearRegression()
            X_reg = y_true_sample.reshape(-1, 1)
            reg.fit(X_reg, y_pred_sample)
            
            # Create line points for plotting
            X_line = np.linspace(min_val, max_val, 100).reshape(-1, 1)
            y_line = reg.predict(X_line)
            
            ax.plot(X_line, y_line, color='red', linewidth=2, label='Best fit')
            
            # Calculate statistics
            r2 = r2_score(y_true_sample, y_pred_sample)
            mae = mean_absolute_error(y_true_sample, y_pred_sample)
            rmse = np.sqrt(mean_squared_error(y_true_sample, y_pred_sample))
            
            # Add statistics text
            ax.text(0.05, 0.95, f"$R^2$={r2:.3f}\nMAE={mae:.2f}\nRMSE={rmse:.2f}",
                    transform=ax.transAxes, fontsize=12,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # Set labels and title
            ax.set_xlabel('Local UTCI (°C)', fontsize=12)
            ax.set_ylabel('Global UTCI (°C)', fontsize=12)
            ax.set_title(f'{city_name}: UTCI {mask_name} at {t}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Set consistent axis limits
            ax.set_xlim(min_val-0.5, max_val+0.5)
            ax.set_ylim(min_val-0.5, max_val+0.5)
            ax.set_aspect('equal', adjustable='box')
            
            # Save the plot
            output_path = output_dir / f"utci_scatter_{mask_name}_{t}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {output_path}")
    
    # Also create 3x1 subplot for each mask type (for comparison)
    for mask_name in MASK_LABELS.keys():
        timestamps_with_data = [t for t in time_steps if t in all_data and mask_name in all_data[t]]
        
        if not timestamps_with_data:
            continue
            
        fig, axes = plt.subplots(1, len(timestamps_with_data), figsize=(6*len(timestamps_with_data), 6))
        if len(timestamps_with_data) == 1:
            axes = [axes]
        
        colors = ['blue', 'orange', 'green'] 
        
        for i, t in enumerate(timestamps_with_data):
            data = all_data[t][mask_name]
            y_true_sample = data['local']
            y_pred_sample = data['global']
            
            # Create scatter plot
            axes[i].scatter(y_true_sample, y_pred_sample, alpha=0.6, s=1, color=colors[i % len(colors)])
            
            # Add 1:1 line
            min_val, max_val = axis_ranges[t]
            axes[i].plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='1:1 line')
            
            # Add best fit line
            from sklearn.linear_model import LinearRegression
            reg = LinearRegression()
            X_reg = y_true_sample.reshape(-1, 1)
            reg.fit(X_reg, y_pred_sample)
            
            X_line = np.linspace(min_val, max_val, 100).reshape(-1, 1)
            y_line = reg.predict(X_line)
            
            axes[i].plot(X_line, y_line, color='red', linewidth=2, label='Best fit')
            
            # Calculate statistics
            r2 = r2_score(y_true_sample, y_pred_sample)
            mae = mean_absolute_error(y_true_sample, y_pred_sample)
            rmse = np.sqrt(mean_squared_error(y_true_sample, y_pred_sample))
            
            # Add statistics text
            axes[i].text(0.05, 0.95, f"$R^2$={r2:.3f}\nMAE={mae:.2f}\nRMSE={rmse:.2f}",
                        transform=axes[i].transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            axes[i].set_xlabel('Local UTCI (°C)')
            axes[i].set_ylabel('Global UTCI (°C)')
            axes[i].set_title(f'{t}')
            axes[i].grid(True, alpha=0.3)
            axes[i].legend()
            
            # Set consistent axis limits for this timestamp
            axes[i].set_xlim(min_val, max_val)
            axes[i].set_ylim(min_val, max_val)
            axes[i].set_aspect('equal', adjustable='box')
        
        fig.suptitle(f'{city_name}: UTCI Pixel Scatter {mask_name}', fontsize=16)
        plt.tight_layout()
        
        # Save the combined plot
        output_path = output_dir / f"utci_pixel_scatter_{mask_name}_3x1.png"
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
        plt.plot(subset['Time'], subset['Mean True'], marker='o', label='Local', color='blue', linewidth=2)
        plt.plot(subset['Time'], subset['Mean Pred'], marker='o', label='Global', color='orange', linewidth=2)
        
        # Add standard deviation bands for Local (True) data
        plt.fill_between(subset['Time'], 
                        subset['Mean True'] - subset['Std True'], 
                        subset['Mean True'] + subset['Std True'], 
                        color='blue', alpha=0.2, label='Local ± Std')
        
        # Add standard deviation bands for Global (Pred) data
        plt.fill_between(subset['Time'], 
                        subset['Mean Pred'] - subset['Std Pred'], 
                        subset['Mean Pred'] + subset['Std Pred'], 
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

def plot_utci_error_lines(metrics_csv, output_dir, city_name):
    """Generate error line plots from CSV metrics"""
    df = pd.read_csv(metrics_csv)
    masks = df['Mask'].unique()

    for mask in masks:
        subset = df[df['Mask'] == mask]
        if subset.empty:
            continue

        plt.figure(figsize=(5, 5))
        plt.plot(subset['Time'], subset['MAE'], marker='o', color='crimson', label='MAE')
        subset = subset.copy()
        subset['Signed Error'] = subset['Mean Pred'] - subset['Mean True']
        plt.plot(subset['Time'], subset['Signed Error'], marker='s', color='green', label='Signed Error')

        plt.xlabel('Time')
        plt.ylabel('UTCI Error (°C)')
        plt.title(f'{city_name}: UTCI Error over Time - {mask}')
        plt.axhline(0, linestyle='--', color='gray')
        plt.legend()
        plt.tight_layout()
        out_path = Path(output_dir) / f'utci_error_line_{mask}.png'
        plt.savefig(out_path, dpi=300)
        plt.close()

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    # ‼️ change the city name here based on the city name in city_config.yaml
    city_name = "RiodeJaneiro"
    config = {"city": city_name, **all_configs[city_name]}

    # local file paths
    local_utci_paths = config['utci_local_paths']
    global_utci_paths = config['utci_global_paths']
    shade_paths = config['shade_local_paths']
    
    metrics_csv = f"results/utci/{city_name}/metrics/utci_stats_{city_name}.csv"
    output_dir = Path(f"results/utci/{city_name}/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # generate all plots
    plot_utci_pixel_scatter(local_utci_paths, global_utci_paths, shade_paths, output_dir, city_name)
    plot_utci_lines(metrics_csv, output_dir, city_name)
    plot_utci_error_lines(metrics_csv, output_dir, city_name)

    print("✅ All UTCI plots generated.")

if __name__ == "__main__":
    main() 