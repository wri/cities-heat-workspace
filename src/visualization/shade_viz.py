import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import yaml


def load_metrics(input_dir, city_name):
    # accuracy_all_df = pd.read_csv(input_dir / f"shade_accuracy_all_{city_name}.csv")
    accuracy_weighted_df = pd.read_csv(input_dir / f"shade_accuracy_weighted_{city_name}.csv")
    kappa_df = pd.read_csv(input_dir / f"shade_kappa_{city_name}.csv")
    confusion_df = pd.read_csv(input_dir / f"shade_confusion_matrix_all_{city_name}.csv")
    return accuracy_weighted_df, kappa_df, confusion_df

# def plot_kappa_table(kappa_df):
#     print("\n📊 Kappa Coefficients by Time:")
#     print(kappa_df.to_string(index=False))

# def plot_confusion_matrices(confusion_df, output_dir):
#     times = confusion_df['Time'].unique()
#     labels = ["Building Shade", "Tree Shade", "No Shade"]
#     for t in times:
#         plt.figure(figsize=(6, 5))
#         subset = confusion_df[confusion_df["Time"] == t].pivot(
#             index="Actual Class", columns="Predicted Class", values="Count")
#         sns.heatmap(subset, annot=True, fmt="d", cmap="Blues", cbar=False)
#         plt.title(f"Confusion Matrix ({t})")
#         plt.ylabel("Actual Class (LiDAR)")
#         plt.xlabel("Predicted Class (Global)")
#         plt.tight_layout()
#         plt.savefig(output_dir / f"confusion_matrix_{t}.png")
#         plt.close()

# bar plot for user & producer accuracy (weighted) with kappa coefficient by time
def plot_weighted_accuracy_with_kappa(accuracy_weighted_df, kappa_df, output_dir):
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
        # bars1 = ax.bar(x - width/2, prod_acc * 100, width, label='Weighted Producer Accuracy', color="#8BC34A")
        # bars2 = ax.bar(x + width/2, user_acc * 100, width, label='Weighted User Accuracy', color="#03A9F4")

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
        ax.set_title(f"{t}: Shade Accuracy (Weighted)")
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

        output_path = output_dir / f"shade_weighted_accuracy_{t}.png"
        plt.savefig(output_path, dpi=300)
        print(f"✅ Saved weighted plot for {t} to {output_path}")
        plt.close()

# shade area distribution percentage by time
def plot_percentage_bar_by_time(df, output_dir):
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
        ax.set_title(f"{t} - Shade Area Distribution (%)")
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

        output_path = output_dir / f"shade_area_distribution_percentage_{t}.png"
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

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    city_name = "Monterrey2"
    config = {"city": city_name, **all_configs[city_name]}
    USE_SIGNED_ERROR = True  # Toggle between signed and absolute error

    input_dir = Path(f"results/shade/{city_name}/metrics")
    output_dir = Path(f"results/shade/{city_name}/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)
    accuracy_df, kappa_df, confusion_df = load_metrics(input_dir, city_name)
    # plot_kappa_table(kappa_df)
    # plot_confusion_matrices(confusion_df, output_dir)
    plot_weighted_accuracy_with_kappa(accuracy_df, kappa_df, output_dir)
    plot_percentage_bar_by_time(confusion_df, output_dir)
    plot_shade_error_over_time(confusion_df, output_dir, signed=USE_SIGNED_ERROR)
    plot_shade_difference_raw(confusion_df, output_dir)

if __name__ == "__main__":
    main()