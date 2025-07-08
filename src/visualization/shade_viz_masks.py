import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import yaml


# TODO: incorporate into main shade_viz file

# load metrics for a specific mask
def load_metrics_for_mask(input_dir, city_name, mask_name):
    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    
    accuracy_weighted_df = pd.read_csv(input_dir / f"shade_accuracy_weighted_{city_name}{mask_suffix}.csv")
    kappa_df = pd.read_csv(input_dir / f"shade_kappa_all_{city_name}{mask_suffix}.csv")
    confusion_df = pd.read_csv(input_dir / f"shade_confusion_matrix_all_{city_name}{mask_suffix}.csv")
    
    return accuracy_weighted_df, kappa_df, confusion_df


def plot_weighted_accuracy_with_kappa(accuracy_weighted_df, kappa_df, output_dir, mask_name):
    shade_classes = ["Building Shade", "Tree Shade", "No Shade"]
    times = sorted(accuracy_weighted_df["Time"].unique())

    for t in times:
        acc_subset = accuracy_weighted_df[accuracy_weighted_df["Time"] == t]
        kappa_value = kappa_df[kappa_df["Time"] == t]["Kappa Coefficient"].values[0]

        x = np.arange(len(shade_classes))  # label locations
        width = 0.35

        # Use weighted accuracy instead of raw
        prod_acc = acc_subset.set_index("Class").loc[shade_classes]["Weighted Prod Acc"].values
        user_acc = acc_subset.set_index("Class").loc[shade_classes]["Weighted User Acc"].values

        fig, ax = plt.subplots(figsize=(5, 5))
        bars1 = ax.bar(x - width/2, prod_acc * 100, width, label='Weighted Producer Accuracy', color="blue", alpha=0.8)
        bars2 = ax.bar(x + width/2, user_acc * 100, width, label='Weighted User Accuracy', color="orange", alpha=0.8)

        # Annotate bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{height:.2f}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

        ax.set_ylabel("Weighted Accuracy (%)")
        ax.set_title(f"{mask_name.title()}: {t} - Shade Accuracy (Weighted)")
        ax.set_xticks(x)
        ax.set_xticklabels(shade_classes, rotation=10)
        ax.set_ylim(0, 100)
        ax.legend(loc='upper left')
        
        # Position the kappa text right under the legend
        legend = ax.get_legend()
        legend_bbox = legend.get_window_extent().transformed(ax.transAxes.inverted())
        plt.text(legend_bbox.x0, legend_bbox.y0 - 0.02, f"Kappa Coefficient: {kappa_value:.2f}",
                 transform=ax.transAxes, fontsize=9, verticalalignment='top', horizontalalignment='left')
        plt.tight_layout()

        mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
        output_path = output_dir / f"shade_weighted_accuracy_{t}{mask_suffix}.png"
        plt.savefig(output_path, dpi=300)
        print(f"✅ Saved weighted plot for {mask_name} - {t} to {output_path}")
        plt.close()


def plot_percentage_bar_by_time(df, output_dir, mask_name):
    """Plot shade area distribution percentage by time for a specific mask"""
    shade_labels = ["Building Shade", "Tree Shade", "No Shade"]
    times = sorted(df["Time"].unique())

    for t in times:
        subset = df[df["Time"] == t]

        # Local (Actual)
        actual_counts = subset.groupby("Actual Class")["Count"].sum()
        actual_counts = actual_counts.reindex(shade_labels, fill_value=0)
        total_actual = actual_counts.sum()
        actual_perc = (actual_counts / total_actual * 100).round(2)

        # Global (Predicted)
        pred_counts = subset.groupby("Predicted Class")["Count"].sum()
        pred_counts = pred_counts.reindex(shade_labels, fill_value=0)
        total_pred = pred_counts.sum()
        pred_perc = (pred_counts / total_pred * 100).round(2)

        x = np.arange(len(shade_labels))  # label positions
        width = 0.35

        fig, ax = plt.subplots(figsize=(5, 5))
        bars1 = ax.bar(x - width/2, actual_perc, width, label='Local (Actual)', color="blue", alpha=0.8)
        bars2 = ax.bar(x + width/2, pred_perc, width, label='Global (Predicted)', color="orange", alpha=0.8)

        ax.set_ylabel("Percentage of Area (%)")
        ax.set_title(f"{mask_name.title()}: {t} - Shade Area Distribution (%)")
        ax.set_xticks(x)
        ax.set_xticklabels(shade_labels)
        ax.set_ylim(0, 100)
        ax.legend()
        plt.tight_layout()

        # Annotate bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 1,
                    f"{height:.1f}",
                    ha='center',
                    va='bottom',
                    fontsize=10
                )

        mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
        output_path = output_dir / f"shade_area_distribution_percentage_{t}{mask_suffix}.png"
        plt.savefig(output_path)
        print(f"✅ Saved: {output_path}")
        plt.close()


def plot_shade_error_over_time(df, output_dir, mask_name, signed=True):
    """Plot shade error over time for a specific mask"""
    shade_labels = ["Building Shade", "Tree Shade", "No Shade"]
    times = sorted(df["Time"].unique())
    error_data = {label: [] for label in shade_labels}

    for t in times:
        subset = df[df["Time"] == t]

        actual_counts = subset.groupby("Actual Class")["Count"].sum()
        actual_counts = actual_counts.reindex(shade_labels, fill_value=0)

        pred_counts = subset.groupby("Predicted Class")["Count"].sum()
        pred_counts = pred_counts.reindex(shade_labels, fill_value=0)

        for label in shade_labels:
            actual = actual_counts[label]
            pred = pred_counts[label]

            epsilon = 1e-6  # avoid division by zero
            diff = pred - actual
            denominator = actual + epsilon
            error = (diff / denominator * 100) if signed else (abs(diff) / denominator * 100)

            error_data[label].append(error)

    # Plot line graph
    plt.figure(figsize=(8, 5))
    for label in shade_labels:
        y = error_data[label]
        plt.plot(times, y, marker='o', label=label)

        # Annotate with % value
        for i, val in enumerate(y):
            offset = -6  # always place below
            plt.text(
                times[i], val + offset,
                f"{val:.1f}%",
                ha="center",
                va="top",
                fontsize=9
            )

    y_label = "Over/underestimation (%)" if signed else "Absolute % Error in Area"
    plt.title(f"{mask_name.title()}: {y_label} by Shade Type over Time")
    plt.xlabel("Time")
    plt.ylabel(y_label)
    all_errors = [e for v in error_data.values() for e in v if not np.isnan(e)]
    if all_errors:  # Check if we have valid errors
        plt.ylim(min(min(all_errors)-5, -10), max(all_errors)+5)
    plt.axhline(0, linestyle='--', color='gray', linewidth=1)
    plt.legend()
    plt.tight_layout()

    suffix = "signed" if signed else "absolute"
    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    output_path = output_dir / f"shade_error_by_type_{suffix}{mask_suffix}.png"
    plt.savefig(output_path)
    print(f"✅ Saved: {output_path}")
    plt.close()


def plot_shade_difference_raw(df, output_dir, mask_name):
    """Plot raw shade difference for a specific mask"""
    shade_labels = ["Building Shade", "Tree Shade", "No Shade"]
    times = sorted(df["Time"].unique())
    diff_data = {label: [] for label in shade_labels}

    for t in times:
        subset = df[df["Time"] == t]

        actual_counts = subset.groupby("Actual Class")["Count"].sum()
        actual_counts = actual_counts.reindex(shade_labels, fill_value=0)

        pred_counts = subset.groupby("Predicted Class")["Count"].sum()
        pred_counts = pred_counts.reindex(shade_labels, fill_value=0)

        for label in shade_labels:
            diff = pred_counts[label] - actual_counts[label]
            diff_data[label].append(diff)

    # Plot line graph
    plt.figure(figsize=(8, 5))
    for label in shade_labels:
        y = diff_data[label]
        plt.plot(times, y, marker='o', label=label)
        for i, val in enumerate(y):
            offset = 20000 if val >= 0 else -20000
            plt.text(
                times[i], val + offset,
                f"{val:+,}", ha="center", fontsize=9
            )

    plt.title(f"{mask_name.title()}: Raw Count Difference in Shade Area by Type Over Time")
    plt.xlabel("Time")
    plt.ylabel("Predicted (Global) - Actual (Local) (pixels)")
    plt.axhline(0, linestyle='--', color='gray', linewidth=1)
    plt.legend(loc='upper right')
    plt.tight_layout()

    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    output_path = output_dir / f"shade_difference_by_type_raw{mask_suffix}.png"
    plt.savefig(output_path)
    print(f"✅ Saved: {output_path}")
    plt.close()


def visualize_mask(city_name, mask_name, input_dir, output_dir, use_signed_error=True):
    """Generate all visualizations for a specific mask"""
    print(f"\nGenerating visualizations for {city_name} - {mask_name}")
    
    # Check if metrics files exist
    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    required_files = [
        f"shade_accuracy_weighted_{city_name}{mask_suffix}.csv",
        f"shade_kappa_all_{city_name}{mask_suffix}.csv",
        f"shade_confusion_matrix_all_{city_name}{mask_suffix}.csv"
    ]
    
    for file in required_files:
        if not (input_dir / file).exists():
            print(f"⚠️  Skipping {mask_name} - missing file: {file}")
            return
    
    # Load metrics
    try:
        accuracy_df, kappa_df, confusion_df = load_metrics_for_mask(input_dir, city_name, mask_name)
        
        # Generate all plots
        plot_weighted_accuracy_with_kappa(accuracy_df, kappa_df, output_dir, mask_name)
        plot_percentage_bar_by_time(confusion_df, output_dir, mask_name)
        plot_shade_error_over_time(confusion_df, output_dir, mask_name, signed=use_signed_error)
        plot_shade_difference_raw(confusion_df, output_dir, mask_name)
        
        print(f"✅ All visualizations completed for {mask_name}")
        
    except Exception as e:
        print(f"❌ Error generating visualizations for {mask_name}: {e}")


def visualize_shade_all_masks(config, resolution="1m", use_signed_error=True):
    """Generate visualizations for all masks at specified resolution"""
    city = config['city']
    
    # Select mask paths based on resolution
    if resolution == "20m":
        mask_paths = config.get('mask_paths_20m', {})
        if not mask_paths:
            print(f"⚠️  20m mask paths not found, falling back to 1m resolution")
            mask_paths = config.get('mask_paths', {})
            resolution = "1m"
    else:
        mask_paths = config.get('mask_paths', {})
    
    # define masks
    masks = {
        "pedestrian": mask_paths.get('pedestrian_mask_path'),
        "non_building": mask_paths.get('land_use_mask_path')
    }
    
    print(f"Available mask paths for {resolution}: {mask_paths}")
    
    print(f"Starting shade visualization for {city} at {resolution} resolution")
    print(f"   Masks to visualize: {list(masks.keys())}")

    for mask_name, mask_path in masks.items():
        if mask_path is None:
            print(f"⚠️  Skipping {mask_name} - no mask path provided")
            continue
        
        # Set input and output directories based on resolution
        if resolution == "20m":
            input_dir = Path(f"results/shade/{city}/20m/{mask_name}/metrics")
            output_dir = Path(f"results/shade/{city}/20m/{mask_name}/graphs")
        else:
            input_dir = Path(f"results/shade/{city}/{mask_name}/metrics")
            output_dir = Path(f"results/shade/{city}/{mask_name}/graphs")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        visualize_mask(city, mask_name, input_dir, output_dir, use_signed_error)

    print(f"\n✅ All shade visualizations completed for {city} at {resolution} resolution")


def main():
    # ‼️ configuration - change these values as needed
    city_name = "Monterrey1"
    resolution = "20m"  # "1m" or "20m"
    USE_SIGNED_ERROR = True  # toggle between signed and absolute error
    
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    config = {"city": city_name, **all_configs[city_name]}
    print(f"Running shade visualization for {city_name} at {resolution} resolution...")
    visualize_shade_all_masks(config, resolution, USE_SIGNED_ERROR)


if __name__ == "__main__":
    main() 