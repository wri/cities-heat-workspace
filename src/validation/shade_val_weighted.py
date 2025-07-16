import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import pandas as pd
from pathlib import Path
import yaml
import requests

# check if file exists locally
def file_exists_locally(file_path):
    return Path(file_path).exists()

# use url if not locally available
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

def classify_raster(data):
    shade_classes = {0.00: 0, 0.03: 1, 1.00: 2}
    classified = np.full(data.shape, -1, dtype=np.int8)
    for val, label in shade_classes.items():
        mask = np.isclose(data, val, atol=0.0005)
        classified[mask] = label
    return classified

def get_overlap_window(src1, src2):
    if src1.crs != src2.crs:
        bounds2 = transform_bounds(src2.crs, src1.crs, *src2.bounds)
    else:
        bounds2 = src2.bounds
    overlap_bounds = BoundingBox(
        max(src1.bounds.left, bounds2.left),
        max(src1.bounds.bottom, bounds2.bottom),
        min(src1.bounds.right, bounds2.right),
        min(src1.bounds.top, bounds2.top)
    )
    if (overlap_bounds.right <= overlap_bounds.left) or (overlap_bounds.top <= overlap_bounds.bottom):
        raise ValueError("No overlapping region between rasters.")
    window1 = from_bounds(*overlap_bounds, transform=src1.transform)
    window2 = from_bounds(*overlap_bounds, transform=src2.transform)
    return window1.round_offsets(), window2.round_offsets()

def shrink_window(window, n_pixels):
    return Window(
        window.col_off + n_pixels,
        window.row_off + n_pixels,
        window.width - 2 * n_pixels,
        window.height - 2 * n_pixels
    )

# def per_class_kappa(conf_mat):
#     n_classes = conf_mat.shape[0]
#     total = conf_mat.sum()
#     row_marginals = conf_mat.sum(axis=1)
#     col_marginals = conf_mat.sum(axis=0)

#     kappas = []
#     for i in range(n_classes):
#         p0 = conf_mat[i, i] / total if total > 0 else 0
#         pe = (row_marginals[i] * col_marginals[i]) / (total ** 2) if total > 0 else 0
#         kappa_i = (p0 - pe) / (1 - pe) if (1 - pe) != 0 else np.nan
#         kappas.append(kappa_i)
#     return kappas

def validate_shade_from_config(config):
    city = config['city']
    local_shade_paths = config['shade_local_paths']
    global_shade_paths = config['shade_global_paths']
    output_dir = Path(f"results/shade/{city}/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    base_time_steps = [Path(path).stem.split('_')[-1] for path in local_shade_paths]
    class_labels = ["Building Shade", "Tree Shade", "No Shade"]

    weighted_results = []
    kappa_results = []
    per_class_kappa_results = []
    confusion_results = []

    for time, local_path, global_path in zip(base_time_steps, local_shade_paths, global_shade_paths):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global:
                if src_local.crs != src_global.crs:
                    raise ValueError("CRS mismatch. Reproject manually before validation.")

                if src_local.transform != src_global.transform or src_local.shape != src_global.shape:
                    print(f"❗️ {time}: Raster mismatch. Cropping.")
                    win_local, win_global = get_overlap_window(src_local, src_global)
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    raw_local = src_local.read(1, window=win_local)
                    raw_global = src_global.read(1, window=win_global)
                else:
                    print(f"✅ {time}: Aligned. Proceeding.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    raw_local = src_local.read(1, window=window)
                    raw_global = src_global.read(1, window=window)

        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue

        local_data = classify_raster(raw_local)
        global_data = classify_raster(raw_global)

        mask = (local_data != -1) & (global_data != -1)
        y_true = local_data[mask].flatten()
        y_pred = global_data[mask].flatten()

        if y_true.size == 0 or y_pred.size == 0:
            print(f"❌ [{time}] No valid classified pixels after masking. Skipping.")
            continue

        conf_mat = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
        print(f"\n🔍 [{time}] Confusion Matrix:")
        print(pd.DataFrame(conf_mat, index=class_labels, columns=class_labels))

        # # Per-class Kappa
        # class_kappas = per_class_kappa(conf_mat)
        # for label, k in zip(class_labels, class_kappas):
        #     per_class_kappa_results.append({"Time": time, "Class": label, "Per-Class Kappa": k})

        # weighted accuracy
        total_pixels = conf_mat.sum()
        for i, label in enumerate(class_labels):
            actual_total = conf_mat[i, :].sum()
            user_acc = conf_mat[i, i] / conf_mat[:, i].sum() if conf_mat[:, i].sum() > 0 else np.nan
            prod_acc = conf_mat[i, i] / actual_total if actual_total > 0 else np.nan
            weight = actual_total / total_pixels if total_pixels > 0 else 0
            weighted_results.append({
                "Time": time,
                "Class": label,
                "User Accuracy": round(user_acc, 3),
                "Producer Accuracy": round(prod_acc, 3),
                "Weight": round(weight, 4),
                "Weighted User Acc": round(user_acc * weight, 4) if not np.isnan(user_acc) else np.nan,
                "Weighted Prod Acc": round(prod_acc * weight, 4) if not np.isnan(prod_acc) else np.nan 
                })

        

        overall_kappa = cohen_kappa_score(y_true, y_pred)
        
        # TODO: check this method... still doubtful if this is correct
        # but this weight assuemes class as ordinal, which is not the case
        # overall_kappa_weighted = cohen_kappa_score(y_true, y_pred, weights='linear') 

        # save results
        kappa_results.append({"Time": time, "Kappa Coefficient": overall_kappa})

        # save confusion matrix
        for i, row_label in enumerate(class_labels):
            for j, col_label in enumerate(class_labels):
                confusion_results.append({
                    "Time": time,
                    "Actual Class": row_label,
                    "Predicted Class": col_label,
                    "Count": conf_mat[i, j]
                })

    # save results
    pd.DataFrame(kappa_results).to_csv(output_dir / f"shade_kappa_{city}.csv", index=False)
    pd.DataFrame(weighted_results).to_csv(output_dir / f"shade_accuracy_weighted_{city}.csv", index=False)
    pd.DataFrame(confusion_results).to_csv(output_dir / f"shade_confusion_matrix_all_{city}.csv", index=False)
    print(f"✅ Shade validation complete for {city}. Results saved to {output_dir.resolve()}")

def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    city_name = "Monterrey2"
    config = {"city": city_name, **all_configs[city_name]}

    # check if local files exist, otherwise download from url
    local_shade_paths = config['shade_local_paths']
    global_shade_paths = config['shade_global_paths']
    for local_path, global_path in zip(local_shade_paths, global_shade_paths):
        if not file_exists_locally(local_path):
            download_from_url(config['url_local_shade'], local_path)
        if not file_exists_locally(global_path):
            download_from_url(config['url_global_shade'], global_path)

    validate_shade_from_config(config)

if __name__ == "__main__":
    main() 