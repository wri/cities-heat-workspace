import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

CSV_PATH = "results/shade/Monterrey1/shade_confusion_matrix_all_Monterrey1.csv"
OUTPUT_DIR = Path("results/shade/Monterrey1/viz/confusion_matrices")
SHADE_CLASSES = ["Building Shade", "Tree Shade", "No Shade"]

def generate_matrix_with_totals(df, time):
    subset = df[df["Time"] == time]
    matrix = subset.pivot_table(
        index="Actual Class",
        columns="Predicted Class",
        values="Count",
        aggfunc="sum",
        fill_value=0
    ).reindex(index=SHADE_CLASSES, columns=SHADE_CLASSES, fill_value=0)

    # Add totals
    matrix["Total (Actual)"] = matrix.sum(axis=1)
    total_row = matrix.sum(axis=0)
    total_row.name = "Total (Predicted)"
    matrix = pd.concat([matrix, total_row.to_frame().T])

    return matrix

def format_annotations(matrix):
    # Generate annotation strings with count and %
    total = matrix.loc[SHADE_CLASSES, SHADE_CLASSES].values.sum()
    annotations = matrix.copy().astype(str)

    for row in SHADE_CLASSES:
        for col in SHADE_CLASSES:
            count = matrix.loc[row, col]
            perc = (count / total * 100) if total > 0 else 0
            annotations.loc[row, col] = f"{count:,.0f}\n({perc:.1f}%)"

    # Leave totals unannotated or annotate separately
    for col in annotations.columns:
        if "Total" in col:
            annotations[col] = matrix[col].map("{:,.0f}".format)
    for row in annotations.index:
        if "Total" in row:
            annotations.loc[row] = matrix.loc[row].map("{:,.0f}".format)

    return annotations

def plot_confusion_heatmap(matrix, annotations, time, output_dir):
    fig, ax = plt.subplots(figsize=(9, 6))

    sns.heatmap(
        matrix,
        annot=annotations,
        fmt="",
        cbar=False,
        linewidths=0.5,
        linecolor='black',
        cmap="Greys",
        square=True,
        ax=ax
    )

    ax.set_title(f"{time} Confusion Matrix", fontsize=14, pad=20)
    ax.set_xlabel("Global (Predicted)", fontsize=12)
    ax.set_ylabel("LiDAR (Actual)", fontsize=12)

    plt.tight_layout()
    output_path = output_dir / f"confusion_matrix_seaborn_style_{time}.png"
    plt.savefig(output_path)
    print(f"✅ Saved figure: {output_path}")
    plt.close()

def main():
    df = pd.read_csv(CSV_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for t in sorted(df["Time"].unique()):
        matrix = generate_matrix_with_totals(df, t)
        annotations = format_annotations(matrix)

        # Save to CSV
        csv_path = OUTPUT_DIR / f"confusion_matrix_raw_{t}.csv"
        matrix.to_csv(csv_path)
        print(f"✅ Saved CSV: {csv_path}")

        # Plot heatmap
        plot_confusion_heatmap(matrix, annotations, t, OUTPUT_DIR)

if __name__ == "__main__":
    main()