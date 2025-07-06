import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from pathlib import Path
import yaml
import pandas as pd
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import random

def open_local_raster(file_path):
    return rasterio.open(file_path)

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


def validate_building_footprint_from_config(config):
    city = config['city']
    global_dsm_path = config['global_dsm_path']
    global_dem_path = config['global_dem_path']
    local_dsm_path = config['local_dsm_path']
    local_dem_path = config['local_dem_path']
    output_dir = Path(f"results/buildings/{city}/footprint/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open_local_raster(global_dsm_path) as g_dsm, \
         open_local_raster(global_dem_path) as g_dem, \
         open_local_raster(local_dsm_path) as l_dsm, \
         open_local_raster(local_dem_path) as l_dem:

        # Check alignment & crop to overlap
        if g_dsm.transform != l_dsm.transform or g_dsm.shape != l_dsm.shape:
            print("🟠 DSM mismatch. Cropping.")
            win_g_dsm, win_l_dsm = get_overlap_window(g_dsm, l_dsm)
            win_g_dsm = shrink_window(win_g_dsm, 10)
            win_l_dsm = shrink_window(win_l_dsm, 10)
        else:
            print("🟢 DSM aligned. Proceeding.")
            win_g_dsm = win_l_dsm = shrink_window(Window(0, 0, g_dsm.width, g_dsm.height), 10)

        g_height = g_dsm.read(1, window=win_g_dsm) - g_dem.read(1, window=win_g_dsm)
        l_height = l_dsm.read(1, window=win_l_dsm) - l_dem.read(1, window=win_l_dsm)

        g_mask = g_height > 0
        l_mask = l_height > 0

        # Sample random points
        valid_y, valid_x = np.where((g_mask | l_mask))
        idx = random.sample(range(len(valid_x)), min(500, len(valid_x)))
        sampled_points = [(valid_y[i], valid_x[i]) for i in idx]

        results = []
        for y, x in sampled_points:
            true = int(l_mask[y, x])
            pred = int(g_mask[y, x])
            results.append((true, pred))

        y_true, y_pred = zip(*results)
        conf = confusion_matrix(y_true, y_pred, labels=[0, 1])
        kappa = cohen_kappa_score(y_true, y_pred)

        user_acc = conf[1, 1] / conf[:, 1].sum() if conf[:, 1].sum() > 0 else np.nan
        prod_acc = conf[1, 1] / conf[1, :].sum() if conf[1, :].sum() > 0 else np.nan

        df = pd.DataFrame({
            "City": [city],
            "User Accuracy": [user_acc],
            "Producer Accuracy": [prod_acc],
            "Kappa": [kappa]
        })
        df.to_csv(output_dir / f"building_footprint_accuracy_{city}.csv", index=False)
        print(df)


if __name__ == "__main__":
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)
    
    # change the city name based on the city name in city_config.yaml
    city_name = "RiodeJaneiro"
    config = {"city": city_name, **all_configs[city_name]}
    validate_building_footprint_from_config(config)
