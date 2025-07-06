import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import yaml

def load_confusion_matrix(city):
    path = Path(f"results/shade/{city}/shade_confusion_matrix_all_{city}.csv")
    df = pd.read_csv(path)
    return df

def plot_shade_area_lines(conf_matrix_df, city):
    times = sorted(conf_matrix_df['Time'].unique())
    classes = ["Building Shade", "Tree Shade", "No Shade"]
    global_area = {c: [] for c in classes}
    local_area = {c: [] for c in classes}
    total_area = []

    for time in times:
        df_time = conf_matrix_df[conf_matrix_df["Time"] == time]
        total = df_time.groupby("Actual Class")["Count"].sum().sum()
        total_area.append(total)

        for c in classes:
            local_area[c].append(df_time[df_time["Actual Class"] == c]["Count"].sum())
            global_area[c].append(df_time[df_time["Predicted Class"] == c]["Count"].sum())

    # Add line for total shaded (building + tree)
    local_area["All Shade"] = [local_area["Building Shade"][i] + local_area["Tree Shade"][i] for i in range(len(times))]
    global_area["All Shade"] = [global_area["Building Shade"][i] + global_area["Tree Shade"][i] for i in range(len(times))]

    # Plot
    for label_group, label_dict in zip(
        ["Local", "Global"],
        [local_area, global_area]
    ):
        plt.figure(figsize=(8, 5))
        for label in ["Building Shade", "Tree Shade", "All Shade", "No Shade"]:
            plt.plot(times, label_dict[label], marker="o", label=label)
        plt.title(f"{city}: {label_group} Shade Area Over Time")
        plt.xlabel("Time")
        plt.ylabel("Pixel Count (Area)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"results/shade/{city}/shade_area_line_{label_group.lower()}_{city}.png")
        plt.close()
        print(f"Saved: shade_area_line_{label_group.lower()}_{city}.png")

def plot_shade_area_error_lines(conf_matrix_df, city):
    times = sorted(conf_matrix_df['Time'].unique())
    classes = ["Building Shade", "Tree Shade", "No Shade", "All Shade"]
    area_error = {c: [] for c in classes}

    for time in times:
        df_time = conf_matrix_df[conf_matrix_df["Time"] == time]
        local = df_time.groupby("Actual Class")["Count"].sum().to_dict()
        global_ = df_time.groupby("Predicted Class")["Count"].sum().to_dict()

        # Fill missing with 0
        for c in ["Building Shade", "Tree Shade", "No Shade"]:
            local.setdefault(c, 0)
            global_.setdefault(c, 0)

        # Add "All Shade"
        local["All Shade"] = local["Building Shade"] + local["Tree Shade"]
        global_["All Shade"] = global_["Building Shade"] + global_["Tree Shade"]

        for c in classes:
            error = abs(global_[c] - local[c])
            area_error[c].append(error)

    # Plot
    plt.figure(figsize=(8, 5))
    for label in classes:
        plt.plot(times, area_error[label], marker="o", label=label)
    plt.title(f"{city}: Absolute Error in Shade Area Over Time")
    plt.xlabel("Time")
    plt.ylabel("Error (Pixel Count)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"results/shade/{city}/shade_area_error_line_{city}.png")
    plt.close()
    print(f"Saved: shade_area_error_line_{city}.png")

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    city = "Monterrey1"  # You can make this dynamic with argparse
    if city not in all_configs:
        raise ValueError(f"{city} not found in config.")

    conf_matrix_df = load_confusion_matrix(city)
    plot_shade_area_lines(conf_matrix_df, city)
    plot_shade_area_error_lines(conf_matrix_df, city)

if __name__ == "__main__":
    main()