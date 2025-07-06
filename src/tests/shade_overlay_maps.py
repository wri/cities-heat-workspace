import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from rasterio.io import MemoryFile
from pathlib import Path
import requests
import matplotlib.pyplot as plt
import yaml
import os


SHADE_CLASSES = {
    0.00: 0,   # Building Shade
    0.03: 1,   # Tree Shade
    1.00: 2    # No Shade
}

LABELS = ["Building Shade", "Tree Shade", "No Shade"]
COLORS = {
    (1, 1): 'black',         # Both shaded
    (1, 0): 'blue',          # Only in local (LiDAR)
    (0, 1): 'red'            # Only in global
}


def classify_raster(data):
    classified = np.full(data.shape, -1, dtype=np.int8)
    for val, label in SHADE_CLASSES.items():
        mask = np.isclose(data, val, atol=0.0005)
        classified[mask] = label
    return classified


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


def create_overlay_plot(local_classified, global_classified, shade_class, title, out_path):
    local_mask = (local_classified == shade_class)
    global_mask = (global_classified == shade_class)

    both = local_mask & global_mask
    only_local = local_mask & ~global_mask
    only_global = global_mask & ~local_mask

    overlay = np.full(local_classified.shape, np.nan)
    overlay[both] = 0
    overlay[only_local] = 1
    overlay[only_global] = 2

    cmap = plt.matplotlib.colors.ListedColormap(['black', 'blue', 'red'])

    plt.figure(figsize=(8, 8))
    plt.imshow(overlay, cmap=cmap, interpolation='none')
    handles = [
        plt.Line2D([0], [0], color='black', lw=4, label='Both shaded'),
        plt.Line2D([0], [0], color='blue', lw=4, label='Only in local'),
        plt.Line2D([0], [0], color='red', lw=4, label='Only in global')
    ]
    plt.legend(handles=handles, loc='lower right')
    plt.title(title)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def process_all_shades(config, city):
    local_urls = config['shade_local']
    global_urls = config['shade_global']
    time_steps = [url.split('_')[-1].replace('.tif', '') for url in local_urls]

    out_dir = Path(f"results/visuals/shade_overlay/{city}")
    out_dir.mkdir(parents=True, exist_ok=True)

    for time, local_url, global_url in zip(time_steps, local_urls, global_urls):
        print(f"🌀 Processing Building Shade @ {time}")
        with open_s3_raster(local_url) as src_local, open_s3_raster(global_url) as src_global:
            if src_local.crs != src_global.crs:
                raise ValueError("CRS mismatch. Reproject first.")

            if src_local.transform != src_global.transform or src_local.shape != src_global.shape:
                win_local, win_global = get_overlap_window(src_local, src_global)
                win_local = shrink_window(win_local, 10)
                win_global = shrink_window(win_global, 10)
                raw_local = src_local.read(1, window=win_local)
                raw_global = src_global.read(1, window=win_global)
            else:
                window = shrink_window(Window(0, 0, src_local.width, src_local.height), 10)
                raw_local = src_local.read(1, window=window)
                raw_global = src_global.read(1, window=window)

        local_classified = classify_raster(raw_local)
        global_classified = classify_raster(raw_global)

        for class_val, label in zip(SHADE_CLASSES.values(), LABELS):
            title = f"{label} Overlap at {time} ({city})"
            out_path = out_dir / f"{city}_{label.replace(' ', '_')}_{time}.png"
            create_overlay_plot(local_classified, global_classified, class_val, title, out_path)


if __name__ == "__main__":
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)

    city_name = "Monterrey1"
    config = {"city": city_name, **all_configs[city_name]}
    process_all_shades(config, city_name)