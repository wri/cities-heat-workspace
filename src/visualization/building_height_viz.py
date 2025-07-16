import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import yaml


def plot_building_height_validation(city, local_filtered, global_filtered, height_errors_filtered, metrics, output_dir):
    r2 = metrics['R²']

    # sample data for scatter plot
    sample_fraction = 0.1  # 10% sample
    np.random.seed(42)  

    sample_mask = np.random.rand(len(local_filtered)) < sample_fraction

    local_sampled = local_filtered[sample_mask]
    global_sampled = global_filtered[sample_mask]

    # # histogram of height errors
    # plt.figure(figsize=(6, 6))
    # plt.hist(height_errors_filtered, bins=100, color='blue', edgecolor='gray')
    # plt.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='No Error')
    # plt.title(f"{city}: Building Height Error (Z-score < ±3)")
    # plt.xlabel("Height Error (Global - Local) (m)")
    # plt.ylabel("Frequency (mil)")
    # plt.grid(True, alpha=0.3)
    # plt.legend()
    # plt.savefig(output_dir / "height_error_histogram_zscore_filtered.png", dpi=300, bbox_inches='tight')
    # plt.close()

    # scatter plot: Global vs Local
    plt.figure(figsize=(6, 6))
    plt.scatter(local_sampled, global_sampled, s=0.5, alpha=0.3, color='blue')
    min_val = min(np.min(local_sampled), np.min(global_sampled))
    max_val = max(np.max(local_sampled), np.max(global_sampled))
    plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='1:1 line') # reference line
    m, b = np.polyfit(local_sampled, global_sampled, 1) # line of best fit
    plt.plot(local_sampled, m * local_sampled + b, color="red", label=f"y = {m:.2f}x + {b:.2f}")
    plt.title(f"{city}: Global vs Local Building Height (Z-score < ±3)")
    # plt.text(0.05, 0.95, f"$R^2$ = {r2:.3f}", transform=plt.gca().transAxes, # r2 value
    #          fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.7))
    plt.xlabel("Local (LiDAR) Building Height (m)")
    plt.ylabel("Global BuildingHeight (m)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis('equal')
    plt.savefig(output_dir / "height_scatterplot_zscore_filtered.png", dpi=300, bbox_inches='tight')
    plt.close()

    # scatter plot zoomed-in : Global vs Local
    plt.figure(figsize=(6, 6))
    plt.scatter(local_sampled, global_sampled, s=0.5, alpha=0.3, color='blue')
    min_val = min(np.min(local_sampled), np.min(global_sampled))
    max_val = max(np.max(local_sampled), np.max(global_sampled))
    plt.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='1:1 line') # reference line
    m, b = np.polyfit(local_sampled, global_sampled, 1) # line of best fit
    plt.plot(local_sampled, m * local_sampled + b, color="red", label=f"y = {m:.2f}x + {b:.2f}")
    plt.title(f"{city}: Global vs Local Building Height (Z-score < ±3)")
    # plt.text(0.05, 0.95, f"$R^2$ = {r2:.3f}", transform=plt.gca().transAxes, # r2 value
    #          fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.7))
    plt.xlabel("Local (LiDAR) Building Height (m)")
    plt.ylabel("Global BuildingHeight (m)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis('equal')
    plt.xlim(-10, 0.75*max_val)  # Set x-axis limit
    plt.ylim(-10, 0.75*max_val)  # Set y-axis limit
    plt.savefig(output_dir / "height_scatterplot_zoomed_zscore_filtered.png", dpi=300, bbox_inches='tight')
    plt.close()

    #print(f"min_val: {min_val}, max_val: {max_val}")

    # histogram of height errors
    plt.figure(figsize=(8, 8))
    max_range = 15  # meters
    clipped_errors = height_errors_filtered[
        (height_errors_filtered >= -max_range) & (height_errors_filtered <= max_range)
    ]

    plt.hist(clipped_errors, bins=100, color='skyblue', edgecolor='gray')
    plt.axvline(x=0, color='red', linestyle='--', label='No Error')
    plt.title(f"{city}: Building Height Error (Z-score < ±3)")
    plt.xlabel("Height Error (Global - Local) (m)")
    plt.ylabel("Pixel Count")
    plt.xlim(-max_range, max_range)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "height_error_histogram_z_score_filtered.png", dpi=300, bbox_inches='tight')
    plt.close()


    print(f"✅ Building height plots generated for {city}. Saved to {output_dir.resolve()}")


def plot_metrics_comparison(zscore_metrics, unfiltered_metrics, output_dir, city_name):
    """Create comparison bar plot from CSV metrics"""
    
    metrics_names = ['MAE', 'RMSE', 'Mean_Bias']
    zscore_values = [zscore_metrics[m] for m in metrics_names]
    unfiltered_values = [unfiltered_metrics[m] for m in metrics_names]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(metrics_names))
    width = 0.35
    
    ax.bar(x - width/2, zscore_values, width, label='Z-score Filtered', color='blue', alpha=0.7)
    ax.bar(x + width/2, unfiltered_values, width, label='Unfiltered', color='orange', alpha=0.7)
    
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Error (meters)')
    ax.set_title(f'{city_name}: Building Height Validation Metrics Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_names)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, (zs, uf) in enumerate(zip(zscore_values, unfiltered_values)):
        ax.text(i - width/2, zs + 0.1, f'{zs:.1f}', ha='center', va='bottom')
        ax.text(i + width/2, uf + 0.1, f'{uf:.1f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(output_dir / "metrics_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Metrics comparison plot saved to {output_dir}")




def main():
    """Generate summary plots from existing CSV metrics"""
    
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    # Change the city name based on the city name in city_config.yaml   
    CITY_NAME = "Monterrey1"

    if CITY_NAME not in all_configs:
        raise ValueError(f"{CITY_NAME} not found in config.")
    
    # Check if metrics files exist
    metrics_dir = Path(f"results/buildings/{CITY_NAME}/height/metrics")
    zscore_csv = metrics_dir / "building_height_metrics_filtered_by_zscore.csv"
    unfiltered_csv = metrics_dir / "building_height_metrics_unfiltered.csv"
    
    if not zscore_csv.exists():
        print(f"❌ Metrics file not found: {zscore_csv}")
        print("Please run building_height_path.py first to calculate metrics.")
        return
    
    # Load metrics from CSV
    zscore_metrics = pd.read_csv(zscore_csv).iloc[0].to_dict()
    unfiltered_metrics = pd.read_csv(unfiltered_csv).iloc[0].to_dict()
    
    print(f"✅ Loaded metrics for {CITY_NAME}")
    print(f"   MAE (filtered): {zscore_metrics['MAE']:.2f}m")
    print(f"   R² (filtered): {zscore_metrics['R²']:.3f}")
    print(f"   Mean Bias (filtered): {zscore_metrics['Mean_Bias']:.2f}m")
    
    output_dir = Path(f"results/buildings/{CITY_NAME}/height/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # plot_metrics_comparison(zscore_metrics, unfiltered_metrics, output_dir, CITY_NAME)
    
    print("For detailed plots with actual building data, run building_height_path.py")
    print("which will call plot_building_height_validation() with data arrays.")


if __name__ == "__main__":
    main() 