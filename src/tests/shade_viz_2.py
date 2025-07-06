import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import yaml

# Set the city here for convenience
CITY_NAME = "Monterrey1"
USE_SIGNED_ERROR = True  # Toggle between signed and absolute error

def plot_percentage_bar_by_time(df, output_dir):
    shade_labels = ["Building Shade", "Tree Shade", "No Shade"]
    times = sorted(df["Time"].unique())

    for t in times:
        subset = df[df["Time"] == t]

        # Local (Actual)
        #actual_counts = subset[subset["Actual Class"] == subset["Predicted Class"]].groupby("Actual Class")["Count"].sum()
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

        fig, ax = plt.subplots(figsize=(7, 5))
        bars1 = ax.bar(x - width/2, actual_perc, width, label='Local (Actual)', color="blue", alpha=0.8)
        bars2 = ax.bar(x + width/2, pred_perc, width, label='Global (Predicted)', color="orange", alpha=0.8)

        ax.set_ylabel("Percentage of Area (%)")
        ax.set_title(f"{t} - Shade Distribution (%)")
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
                    f"{height:.1f}%",
                    ha='center',
                    va='bottom',
                    fontsize=10
                )

        output_path = output_dir / f"shade_distribution_percentage_{t}.png"
        plt.savefig(output_path)
        print(f"✅ Saved: {output_path}")
        plt.close()

def plot_shade_error_over_time(df, output_dir, signed=True):
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
    plt.title(f"{y_label} by Shade Type over Time")
    plt.xlabel("Time")
    plt.ylabel(y_label)
    all_errors = [e for v in error_data.values() for e in v if not np.isnan(e)]
    plt.ylim(min(min(all_errors)-5, -10), max(all_errors)+5)
    plt.axhline(0, linestyle='--', color='gray', linewidth=1)
    plt.legend()
    plt.tight_layout()

    suffix = "signed" if signed else "absolute"
    output_path = output_dir / f"shade_error_by_type_{suffix}.png"
    plt.savefig(output_path)
    print(f"✅ Saved: {output_path}")
    plt.close()

def plot_shade_difference_raw(df, output_dir):
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
            plt.text(
                times[i], val + (20000 if val >= 0 else -20000),  # offset
                f"{val:+,}", ha="center", fontsize=9
            )

    plt.title("Raw Count Difference in Shade Area by Type Over Time")
    plt.xlabel("Time")
    plt.ylabel("Predicted (Global) - Actual (Local) (pixels)")
    plt.axhline(0, linestyle='--', color='gray', linewidth=1)
    plt.legend(loc='upper right')
    plt.tight_layout()

    output_path = output_dir / "shade_difference_by_type_raw.png"
    plt.savefig(output_path)
    print(f"✅ Saved: {output_path}")
    plt.close()

if __name__ == "__main__":
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    if CITY_NAME not in all_configs:
        raise ValueError(f"{CITY_NAME} not found in config.")

    csv_path = f"results/shade/{CITY_NAME}/shade_confusion_matrix_all_{CITY_NAME}.csv"
    output_dir = Path(f"results/shade/{CITY_NAME}/viz")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    plot_percentage_bar_by_time(df, output_dir)
    plot_shade_error_over_time(df, output_dir, signed=USE_SIGNED_ERROR)
    plot_shade_difference_raw(df, output_dir)