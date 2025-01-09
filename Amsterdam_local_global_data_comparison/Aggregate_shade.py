import rasterio
import numpy as np
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
import os

def resample_discrete_raster(input_raster, output_raster, target_resolution, method="majority"):
    """
    Resample a raster with discrete values using majority or nearest methods.

    Parameters:
        input_raster (str): Path to the input raster file.
        output_raster (str): Path to save the resampled raster.
        target_resolution (int): Target resolution in meters (e.g., 10, 25).
        method (str): Resampling method ('majority', 'nearest', or 'mode').

    Returns:
        None
    """
    resampling_methods = {
        "majority": Resampling.mode,
        "nearest": Resampling.nearest,
        "mode": Resampling.mode,  # Mode resolves ties arbitrarily
    }

    if method not in resampling_methods:
        raise ValueError(f"Unsupported method: {method}. Use 'majority', 'nearest', or 'mode'.")

    with rasterio.open(input_raster) as src:
        # Calculate scale factors
        scale_factor = target_resolution / src.res[0]

        # Define new transform and dimensions
        new_width = int(src.width / scale_factor)
        new_height = int(src.height / scale_factor)
        new_transform = src.transform * src.transform.scale(scale_factor, scale_factor)

        # Prepare output data array
        resampled_data = np.empty((new_height, new_width), dtype=src.read(1).dtype)

        # Reproject data with the selected resampling method
        reproject(
            source=src.read(1),
            destination=resampled_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=new_transform,
            dst_crs=src.crs,
            resampling=resampling_methods[method],
        )

        # Update metadata
        resampled_metadata = src.meta.copy()
        resampled_metadata.update({
            "height": new_height,
            "width": new_width,
            "transform": new_transform,
            "res": (target_resolution, target_resolution),
        })

        # Save the resampled raster
        with rasterio.open(output_raster, "w", **resampled_metadata) as dst:
            dst.write(resampled_data, 1)

    print(f"Resampled raster saved to {output_raster} using {method} method.")

def batch_resample_difference_maps(main_folder, output_folder, resolutions, methods):
    """
    Batch process resampling for all difference maps in subfolders.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with difference maps.
        output_folder (str): Path to save the resampled maps.
        resolutions (list): List of target resolutions (e.g., [10, 25]).
        methods (list): List of resampling methods (e.g., ['majority', 'nearest']).

    Returns:
        None
    """
    for subfolder in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder)
        if not os.path.isdir(subfolder_path):
            continue

        for time_of_day in ["difference_12.tif", "difference_15.tif", "difference_18.tif"]:
            input_raster = os.path.join(subfolder_path, time_of_day)

            if os.path.exists(input_raster):
                for resolution in resolutions:
                    for method in methods:
                        # Prepare output folder and file path
                        method_folder = os.path.join(output_folder, method)
                        os.makedirs(method_folder, exist_ok=True)
                        resampled_subfolder = os.path.join(method_folder, subfolder)
                        os.makedirs(resampled_subfolder, exist_ok=True)

                        output_raster = os.path.join(
                            resampled_subfolder, f"{time_of_day.split('.')[0]}_{resolution}m.tif"
                        )

                        # Resample raster
                        resample_discrete_raster(input_raster, output_raster, resolution, method=method)

    print(f"All resampling completed. Results saved in {output_folder}.")


# Parameters
main_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_diff_maps"  # Folder containing subfolders with difference maps
output_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_diff_agg"  # Folder to save resampled maps
resolutions = [5, 10]  # Target resolutions in meters
methods = ["majority", "nearest"]  # Resampling methods

# Batch resample difference maps
batch_resample_difference_maps(main_folder, output_folder, resolutions, methods)
