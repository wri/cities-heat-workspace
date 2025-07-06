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


def open_s3_raster(url):
    response = requests.get(url)
    response.raise_for_status()
    memfile = MemoryFile(response.content)
    return memfile.open()


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

    # Open all rasters
    with open_s3_raster(local_dsm) as src_ldsm, open_s3_raster(global_dsm) as src_gdsm, \
         open_s3_raster(local_dem) as src_ldem, open_s3_raster(global_dem) as src_gdem:

        # Check alignment and crop
        if src_ldsm.transform != src_gdsm.transform or src_ldsm.shape != src_gdsm.shape:
            print("🟠 DSM mismatch. Cropping.")
            win_ldsm, win_gdsm = get_overlap_window(src_ldsm, src_gdsm)
            win_ldsm = shrink_window(win_ldsm, 10)
            win_gdsm = shrink_window(win_gdsm, 10)
        else:
            print("🟢 DSM aligned. Proceeding.")
            win_ldsm = win_gdsm = shrink_window(Window(0, 0, src_ldsm.width, src_ldsm.height), 10)

        dsm_local = src_ldsm.read(1, window=win_ldsm)
        dsm_global = src_gdsm.read(1, window=win_gdsm)

        if src_ldem.transform != src_ldsm.transform or src_ldem.shape != src_ldsm.shape:
            win_ldem, _ = get_overlap_window(src_ldem, src_ldsm)
            win_ldem = shrink_window(win_ldem, 10)
        else:
            win_ldem = shrink_window(Window(0, 0, src_ldem.width, src_ldem.height), 10)

        if src_gdem.transform != src_gdsm.transform or src_gdem.shape != src_gdsm.shape:
            win_gdem, _ = get_overlap_window(src_gdem, src_gdsm)
            win_gdem = shrink_window(win_gdem, 10)
        else:
            win_gdem = shrink_window(Window(0, 0, src_gdem.width, src_gdem.height), 10)

        dem_local = src_ldem.read(1, window=win_ldem)
        dem_global = src_gdem.read(1, window=win_gdem)

    # calculate bldg heights
    height_local = dsm_local - dem_local
    height_global = dsm_global - dem_global

    # mask out invalid pixels
    mask = np.isfinite(height_local) & np.isfinite(height_global)
    local_vals = height_local[mask]
    global_vals = height_global[mask]

    # height difference (error)
    height_errors = global_vals - local_vals

    # metrics
    mae = mean_absolute_error(local_vals, global_vals)
    r2 = r2_score(local_vals, global_vals)
    std = np.std(height_errors)

    metrics = {
        "City": city,
        "MAE": mae,
        "R²": r2,
        "STD": std,
        "% Local Valid Pixels": len(local_vals)/len(height_local)*100,
        "% Global Valid Pixels": len(global_vals)/len(height_global)*100
    }
    # save metrics to csv
    pd.DataFrame([metrics]).to_csv(output_dir / "building_height_metrics.csv", index=False)

    # histogram
    plt.figure()
    plt.hist(height_errors, bins=50, color='gray', edgecolor='black')
    plt.title(f"Building Height Error Histogram: {city}")
    plt.xlabel("Height Error (Global - Local) [m]")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.savefig(output_dir / "height_error_histogram.png", dpi=300)
    plt.close()

    # scatterplot
    plt.figure()
    plt.scatter(local_vals, global_vals, s=1, alpha=0.3)
    m, b = np.polyfit(local_vals, global_vals, 1)
    plt.plot(local_vals, m * local_vals + b, color="red", label=f"y = {m:.2f}x + {b:.2f}")
    plt.title(f"Global vs Local Building Height: {city}")
    plt.xlabel("Local (LiDAR) Height [m]")
    plt.ylabel("Global Height [m]")
    plt.legend()
    plt.grid(True)
    plt.savefig(output_dir / "height_scatterplot.png", dpi=300)
    plt.close()

    print(f"✅ Building height validation complete for {city}. Metrics saved to {output_dir.resolve()}")


# def test_read_with_smaller_windows(src, window_size=100):
#     """
#     Test reading a raster file with smaller windows to diagnose read errors.

#     :param src: The rasterio dataset to read from.
#     :param window_size: The size of the window to read.
#     """
#     width, height = src.width, src.height
#     for col_off in range(0, width, window_size):
#         for row_off in range(0, height, window_size):
#             window = Window(col_off, row_off, min(window_size, width - col_off), min(window_size, height - row_off))
#             try:
#                 data = src.read(1, window=window)
#                 print(f"Successfully read window at col_off={col_off}, row_off={row_off}")
#             except Exception as e:
#                 print(f"Failed to read window at col_off={col_off}, row_off={row_off}: {e}")


if __name__ == "__main__":
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    CITY_NAME = "Monterrey1"  

    if CITY_NAME not in all_configs:
        raise ValueError(f"{CITY_NAME} not found in config.")

    local_dsm_url = all_configs[CITY_NAME]['local_dsm']
    global_dsm_url = all_configs[CITY_NAME]['global_dsm']
    local_dem_url = all_configs[CITY_NAME]['local_dem']
    global_dem_url = all_configs[CITY_NAME]['global_dem']

    output_dir = Path(f"results/buildings/{CITY_NAME}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # # Test reading with smaller windows
    # with open_s3_raster(local_dsm_url) as src_ldsm:
    #     print("Testing local DSM with smaller windows:")
    #     test_read_with_smaller_windows(src_ldsm)

    # with open_s3_raster(global_dsm_url) as src_gdsm:
    #     print("Testing global DSM with smaller windows:")
    #     test_read_with_smaller_windows(src_gdsm)

    # with open_s3_raster(local_dem_url) as src_ldem:
    #     print("Testing local DEM with smaller windows:")
    #     test_read_with_smaller_windows(src_ldem)

    # with open_s3_raster(global_dem_url) as src_gdem:
    #     print("Testing global DEM with smaller windows:")
    #     test_read_with_smaller_windows(src_gdem)

    # Proceed with validation
    validate_building_height(CITY_NAME, local_dsm_url, global_dsm_url, local_dem_url, global_dem_url, output_dir)