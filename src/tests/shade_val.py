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
from rasterio.io import MemoryFile


def classify_raster(data):
    shade_classes = {
        0.00: 0,
        0.03: 1,
        1.00: 2
    }
    # -1: invalid, 0: building shade, 1: tree shade, 2: no shade
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

# shrink window 
def shrink_window(window, n_pixels):
    return Window(
        window.col_off + n_pixels,
        window.row_off + n_pixels,
        window.width - 2 * n_pixels,
        window.height - 2 * n_pixels
    )


def open_s3_raster(url):
    response = requests.get(url)
    response.raise_for_status()
    memfile = MemoryFile(response.content)
    return memfile.open()


def validate_shade_from_config(config):
    city = config['city']
    local_shade_urls = config['shade_local']
    global_shade_urls = config['shade_global']
    output_dir = Path(f"results/shade/{city}/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    base_time_steps = [url.split('_')[-1].replace('.tif','') for url in local_shade_urls]
    class_labels = ["Building Shade", "Tree Shade", "No Shade"]

    kappa_results = []
    accuracy_results = []
    mae_results = []
    confusion_results = []

    for time, local_url, global_url in zip(base_time_steps, local_shade_urls, global_shade_urls):
        with open_s3_raster(local_url) as src_local, open_s3_raster(global_url) as src_global:
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

        local_data = classify_raster(raw_local)
        global_data = classify_raster(raw_global)

        # mask out invalid pixels
        mask = (local_data != -1) & (global_data != -1)
        y_true = local_data[mask].flatten() 
        y_pred = global_data[mask].flatten()

        print(f"[{time}] Masked valid pixels: {mask.sum()}")
        print(f"[{time}] Total classified % (local): {np.sum(local_data != -1)/mask.sum()*100}")
        print(f"[{time}] Total classified % (global): {np.sum(global_data != -1)/mask.sum()*100}")

        if y_true.size == 0 or y_pred.size == 0:
            print(f"❌ [{time}] No valid classified pixels after masking. Skipping.")
            continue

        conf_mat = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
        kappa = cohen_kappa_score(y_true, y_pred)

        print(f"\n🔍 [{time}] Confusion Matrix:")
        print(pd.DataFrame(conf_mat, index=class_labels, columns=class_labels))

        kappa_results.append({"Time": time, "Kappa Coefficient": kappa})

        for i, label in enumerate(class_labels):
            # User & Producer Accuracy
            user_acc = conf_mat[i, i] / conf_mat[:, i].sum() if conf_mat[:, i].sum() > 0 else np.nan
            prod_acc = conf_mat[i, i] / conf_mat[i, :].sum() if conf_mat[i, :].sum() > 0 else np.nan
            accuracy_results.append({
                "Time": time,
                "Class": label,
                "User Accuracy": round(user_acc, 3),
                "Producer Accuracy": round(prod_acc, 3)
            })

            # # MAE (px and %)
            # actual_total = (y_true == i).sum()
            # predicted_total = (y_pred == i).sum()
            # valid_pixel_count = mask.sum()
            # abs_error = abs(predicted_total - actual_total)
            # mae = abs_error / actual_total if actual_total > 0 else np.nan

            # mae_results.append({
            #     "Time": time,
            #     "Class": label,
            #     "MAE": mae,
            #     #"MAE (%)": round(mae_pct, 2)
            # })

        for i, row_label in enumerate(class_labels):
            for j, col_label in enumerate(class_labels):
                confusion_results.append({
                    "Time": time,
                    "Actual Class": row_label,
                    "Predicted Class": col_label,
                    "Count": conf_mat[i, j]
                })

    pd.DataFrame(kappa_results).to_csv(output_dir / f"shade_kappa_all_{city}.csv", index=False)
    pd.DataFrame(accuracy_results).to_csv(output_dir / f"shade_accuracy_all_{city}.csv", index=False)
    # pd.DataFrame(mae_results).to_csv(output_dir / f"shade_mae_all_{city}.csv", index=False)
    pd.DataFrame(confusion_results).to_csv(output_dir / f"shade_confusion_matrix_all_{city}.csv", index=False)
    print(f"✅ Shade validation complete for {city}. Results saved to {output_dir.resolve()}")


if __name__ == "__main__":
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    city_name = "Monterrey1"
    config = {"city": city_name, **all_configs[city_name]}
    validate_shade_from_config(config)