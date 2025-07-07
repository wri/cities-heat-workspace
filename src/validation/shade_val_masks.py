import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import pandas as pd
from pathlib import Path
import yaml

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
# mask to where value is 1
def apply_mask_intersection(data, mask_data):
    if mask_data is None:
        return data
    
    # create a copy to avoid modifying original data
    masked_data = data.copy()
    
    # set pixels to invalid (-1) where mask is not 1
    masked_data[mask_data != 1] = -1
    
    return masked_data

def validate_shade_mask(config, mask_name, mask_path, output_dir, resolution="1m"):
    city = config['city']
    
    # Select paths based on resolution
    if resolution == "20m":
        local_shade_paths = config.get('shade_local_paths_20m', config['shade_local_paths'])
        global_shade_paths = config.get('shade_global_paths_20m', config['shade_global_paths'])
        if 'shade_local_paths_20m' not in config:
            print(f"⚠️  20m paths not found, falling back to 1m resolution")
            resolution = "1m"
    else:
        local_shade_paths = config['shade_local_paths']
        global_shade_paths = config['shade_global_paths']
    
    print(f"Using {resolution} resolution data for validation")

    # Extract time steps, handling both original and resampled file naming
    base_time_steps = []
    for path in local_shade_paths:
        stem = Path(path).stem
        # For resampled files ending with _20m, get the second-to-last part
        if stem.endswith('_20m'):
            time_step = stem.split('_')[-2]
        else:
            time_step = stem.split('_')[-1]
        base_time_steps.append(time_step)
    class_labels = ["Building Shade", "Tree Shade", "No Shade"]

    weighted_results = []
    kappa_results = []
    confusion_results = []

    print(f"\n Processing mask: {mask_name}")
    if mask_path:
        print(f"   Using: {mask_path}")

    for time, local_path, global_path in zip(base_time_steps, local_shade_paths, global_shade_paths):
        print(f"Processing {time}: {local_path} vs {global_path}")
        
        try:
            with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global:
                if src_local.crs != src_global.crs:
                    raise ValueError("CRS mismatch. Reproject manually before validation.")

                # handle mask if provided
                mask_data = None
                if mask_path:
                    with rasterio.open(mask_path) as src_mask:
                        if src_local.crs != src_mask.crs:
                            raise ValueError("Mask CRS mismatch. Reproject mask to match shade data.")

                if src_local.transform != src_global.transform or src_local.shape != src_global.shape:
                    print(f"❗️ {time}: raster mismatch. cropping.")
                    win_local, win_global = get_overlap_window(src_local, src_global)
                    win_local = shrink_window(win_local, 10)
                    win_global = shrink_window(win_global, 10)
                    raw_local = src_local.read(1, window=win_local)
                    raw_global = src_global.read(1, window=win_global)
                    
                    # read mask data if provided
                    if mask_path:
                        with rasterio.open(mask_path) as src_mask:
                            win_mask, _ = get_overlap_window(src_mask, src_local)
                            win_mask = shrink_window(win_mask, 10)
                            mask_data = src_mask.read(1, window=win_mask)
                else:
                    print(f"✅ {time}: Aligned. Proceeding.")
                    window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                    raw_local = src_local.read(1, window=window)
                    raw_global = src_global.read(1, window=window)
                    
                    # read mask data if provided
                    if mask_path:
                        with rasterio.open(mask_path) as src_mask:
                            mask_data = src_mask.read(1, window=window)

        except Exception as e:
            print(f"❌ Error reading files for {time}: {e}")
            continue

        local_data = classify_raster(raw_local)
        global_data = classify_raster(raw_global)

        # apply mask intersection if provided
        if mask_data is not None:
            local_data = apply_mask_intersection(local_data, mask_data)
            global_data = apply_mask_intersection(global_data, mask_data)
            print(f"   🎭 Applied {mask_name} mask - analyzing pixels where mask = 1")

        mask = (local_data != -1) & (global_data != -1)
        y_true = local_data[mask].flatten()
        y_pred = global_data[mask].flatten()

        if y_true.size == 0 or y_pred.size == 0:
            print(f"❌ [{time}] No valid classified pixels after masking. Skipping.")
            continue

        print(f"Valid pixels for analysis: {y_true.size:,}")

        conf_mat = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
        print(f"\n Confusion Matrix:")
        print(pd.DataFrame(conf_mat, index=class_labels, columns=class_labels))

        # weighted accuracy
        total_pixels = conf_mat.sum()
        for i, label in enumerate(class_labels):
            actual_total = conf_mat[i, :].sum()
            user_acc = conf_mat[i, i] / conf_mat[:, i].sum() if conf_mat[:, i].sum() > 0 else np.nan
            prod_acc = conf_mat[i, i] / actual_total if actual_total > 0 else np.nan
            weight = actual_total / total_pixels if total_pixels > 0 else 0
            weighted_results.append({
                "Time": time,
                "mask": mask_name,
                "Class": label,
                "User Accuracy": round(user_acc, 3),
                "Producer Accuracy": round(prod_acc, 3),
                "Weight": round(weight, 4),
                "Weighted User Acc": round(user_acc * weight, 4) if not np.isnan(user_acc) else np.nan,
                "Weighted Prod Acc": round(prod_acc * weight, 4) if not np.isnan(prod_acc) else np.nan
            })

        # overall kappa
        overall_kappa = cohen_kappa_score(y_true, y_pred)
        kappa_results.append({"Time": time, "mask": mask_name, "Kappa Coefficient": overall_kappa})

        # save full confusion matrix
        for i, row_label in enumerate(class_labels):
            for j, col_label in enumerate(class_labels):
                confusion_results.append({
                    "Time": time,
                    "mask": mask_name,
                    "Actual Class": row_label,
                    "Predicted Class": col_label,
                    "Count": conf_mat[i, j]
                })

    # save results with mask-specific naming
    mask_suffix = f"_{mask_name}" if mask_name != "full_area" else ""
    pd.DataFrame(kappa_results).to_csv(output_dir / f"shade_kappa_all_{city}{mask_suffix}.csv", index=False)
    pd.DataFrame(weighted_results).to_csv(output_dir / f"shade_accuracy_weighted_{city}{mask_suffix}.csv", index=False)
    pd.DataFrame(confusion_results).to_csv(output_dir / f"shade_confusion_matrix_all_{city}{mask_suffix}.csv", index=False)
    
    print(f"✅ Shade validation complete for {city} - {mask_name}. Results saved to {output_dir.resolve()}")

def validate_shade_all_masks(config, resolution="1m"):
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
    
    print(f"Starting shade validation for {city} at {resolution} resolution")
    print(f"   masks to process: {list(masks.keys())}")
    
    for mask_name, mask_path in masks.items():
        if mask_path is None:
            print(f"⚠️  Skipping {mask_name} - no mask path provided")
            continue
        
        # create mask-specific output directory with resolution in path
        if resolution == "20m":
            output_dir = Path(f"results/shade/{city}/20m/{mask_name}/metrics")
        else:
            output_dir = Path(f"results/shade/{city}/{mask_name}/metrics")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        validate_shade_mask(config, mask_name, mask_path, output_dir, resolution)


def main():
    # ‼️ configuration - change these values as needed
    city_name = "Monterrey1"
    resolution = "20m"  # "1m" or "20m"
    
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    config = {"city": city_name, **all_configs[city_name]}
    print(f"Running shade validation for {city_name} at {resolution} resolution...")
    validate_shade_all_masks(config, resolution)

if __name__ == "__main__":
    main() 