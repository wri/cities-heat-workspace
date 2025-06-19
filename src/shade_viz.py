# shade_visualize.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def load_metrics(output_dir):
    accuracy_df = pd.read_csv(output_dir / "shade_accuracy_all.csv")
    kappa_df = pd.read_csv(output_dir / "shade_kappa_all.txt")
    confusion_df = pd.read_csv(output_dir / "shade_confusion_matrix_all.csv")
    return accuracy_df, kappa_df, confusion_df

def plot_kappa_table(kappa_df):
    print("\n📊 Kappa Coefficients by Time:")
    print(kappa_df.to_string(index=False))

def plot_confusion_matrices(confusion_df, output_dir):
    times = confusion_df['Time'].unique()
    labels = ["Building Shade", "Tree Shade", "No Shade"]
    for t in times:
        plt.figure(figsize=(6, 5))
        subset = confusion_df[confusion_df["Time"] == t].pivot(
            index="Actual Class", columns="Predicted Class", values="Count")
        sns.heatmap(subset, annot=True, fmt="d", cmap="Blues", cbar=False)
        plt.title(f"Confusion Matrix ({t})")
        plt.ylabel("Actual Class (LiDAR)")
        plt.xlabel("Predicted Class (Global)")
        plt.tight_layout()
        plt.savefig(output_dir / f"confusion_matrix_{t}.png")
        plt.close()

def plot_accuracy_bars(accuracy_df, output_dir):
    plt.figure(figsize=(12, 6))
    melted_acc = pd.melt(accuracy_df, id_vars=["Time", "Class"],
                          value_vars=["User Accuracy", "Producer Accuracy"])
    sns.barplot(data=melted_acc, x="Class", y="value", hue="variable", ci=None)
    plt.title("User & Producer Accuracy by Class")
    plt.ylabel("Accuracy")
    plt.ylim(0, 1)
    plt.legend(title="Metric")
    plt.tight_layout()
    plt.savefig(output_dir / "shade_accuracy_barplot.png")
    plt.close()

def main():
    output_dir = Path("results/shade")
    accuracy_df, kappa_df, confusion_df = load_metrics(output_dir)
    plot_kappa_table(kappa_df)
    plot_confusion_matrices(confusion_df, output_dir)
    plot_accuracy_bars(accuracy_df, output_dir)

if __name__ == "__main__":
    main()