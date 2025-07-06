import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from rasterio.io import MemoryFile
from pathlib import Path
import requests
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
import yaml


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


def validate_building_height(city, local_dsm, global_dsm, local_dem, global_dem, output_dir="results/buildings"):
    output_dir = Path(output_dir) / city
    output_dir.mkdir(parents=True, exist_ok=True)

    with open_local_raster(local_dsm) as src_ldsm, open_local_raster(global_dsm) as src_gdsm, \
         open_local_raster(local_dem) as src_ldem, open_local_raster(global_dem) as src_gdem:

        if src_ldsm.transform != src_gdsm.transform or src_ldsm.shape != src_gdsm.shape:
            print("🟠 DSM mismatch. Cropping.")
            win_ldsm, win_gdsm = get_overlap_window(src_ldsm, src_gdsm)
            win_ldsm = shrink_window(win_ldsm, 10)
            win_gdsm = shrink_window(win_gdsm, 10)
            print(f"DSM Local Window: {win_ldsm}, DSM Global Window: {win_gdsm}")
        else:
            print("🟢 DSM aligned. Proceeding.")
            win_ldsm = win_gdsm = shrink_window(Window(0, 0, src_ldsm.width, src_ldsm.height), 10)

        dsm_local = src_ldsm.read(1, window=win_ldsm)
        dsm_global = src_gdsm.read(1, window=win_gdsm)
        print(f"DSM Local Shape: {dsm_local.shape}, DSM Global Shape: {dsm_global.shape}")

        win_ldem = win_ldsm
        win_gdem = win_gdsm

        dem_local = src_ldem.read(1, window=win_ldem)
        dem_global = src_gdem.read(1, window=win_gdem)
        print(f"DEM Local Shape: {dem_local.shape}, DEM Global Shape: {dem_global.shape}")

    height_local = dsm_local - dem_local
    height_global = dsm_global - dem_global

    mask = np.isfinite(height_local) & np.isfinite(height_global)
    local_vals = height_local[mask].flatten()
    global_vals = height_global[mask].flatten()

    height_errors = global_vals - local_vals

    # Filter out outliers with large absolute errors
    error_threshold = 30  # meters
    abs_error = np.abs(height_errors)
    valid_mask = abs_error < error_threshold

    local_filtered = local_vals[valid_mask]
    global_filtered = global_vals[valid_mask]
    height_errors_filtered = global_filtered - local_filtered

    mae = mean_absolute_error(local_filtered, global_filtered)
    r2 = r2_score(local_filtered, global_filtered)
    std = np.std(height_errors_filtered)

    metrics = {
        "City": city,
        "MAE": mae,
        "R²": r2,
        "STD": std,
        "% Local Valid Pixels": len(local_filtered)/len(height_local.flatten())*100,
        "% Global Valid Pixels": len(global_filtered)/len(height_global.flatten())*100
    }

    pd.DataFrame([metrics]).to_csv(output_dir / "building_height_metrics_filtered.csv", index=False)

    # histogram distribution of bldg height errors
    plt.figure()
    n, bins, patches = plt.hist(height_errors_filtered, bins=50, color='gray', edgecolor='black')
    plt.title(f"Building Height Error Histogram (Filtered < {error_threshold}m): {city}")
    plt.xlabel("Height Error (Global - Local) [m]")
    plt.ylabel("Frequency (millions)")
    plt.grid(True, alpha=0.3)

    # # Add frequency labels to each bar
    # for i in range(len(patches)):
    #     plt.text(patches[i].get_x() + patches[i].get_width() / 2, n[i],
    #              f'{int(n[i])}', ha='center', va='bottom')
    
    plt.savefig(output_dir / "height_error_histogram_filtered.png", dpi=300)
    plt.close()

    # scatterplot of global vs local bldg height
    plt.figure()
    plt.scatter(local_filtered, global_filtered, s=1, alpha=0.3)
    m, b = np.polyfit(local_filtered, global_filtered, 1)
    plt.plot(local_filtered, m * local_filtered + b, color="red", label=f"y = {m:.2f}x + {b:.2f}")
    plt.title(f"Global vs Local Building Height (Filtered < {error_threshold}m): {city}")
    plt.text(0.05, 0.95, f"$R^2$ = {r2:.3f}", transform=plt.gca().transAxes,
         fontsize=10, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.7))
    plt.xlabel("Local (LiDAR) Height [m]")
    plt.ylabel("Global Height [m]")
    plt.legend()
    plt.grid(True)
    plt.savefig(output_dir / "height_scatterplot_filtered.png", dpi=300)
    plt.close()

    print(f"✅ Building height validation complete for {city}. Filtered metrics saved to {output_dir.resolve()}")


if __name__ == "__main__":
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    CITY_NAME = "RiodeJaneiro"

    if CITY_NAME not in all_configs:
        raise ValueError(f"{CITY_NAME} not found in config.")

    local_dsm_path = all_configs[CITY_NAME]['local_dsm_path']
    global_dsm_path = all_configs[CITY_NAME]['global_dsm_path']
    local_dem_path = all_configs[CITY_NAME]['local_dem_path']
    global_dem_path = all_configs[CITY_NAME]['global_dem_path']

    output_dir = Path(f"results/buildings/{CITY_NAME}")
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_building_height(CITY_NAME, local_dsm_path, global_dsm_path, local_dem_path, global_dem_path, output_dir)