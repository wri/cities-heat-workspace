import os
import numpy as np
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
import rasterio
from shade_area_calculation import read_raster, get_bbx_with_edge_buffer, crop_to_bbx
from shade_compare import align_raster, save_difference_raster

def overlay_and_calculate_difference_tmrt(main_folder, output_folder, base_run, edge_buffer=500):
    """
    Overlay Tmrt maps, calculate differences with a base run, and save difference maps as TIFF files.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with Tmrt maps.
        output_folder (str): Path to save the difference maps.
        base_run (str): Subfolder name to be used as the base run.
        edge_buffer (int): Buffer distance (in meters) to crop from each edge.

    Returns:
        None
    """
    # Keys to locate time-of-day Tmrt maps
    time_keys = ["Tmrt_2023_189_1200D", "Tmrt_2023_189_1500D", "Tmrt_2023_189_1800D"]
    time_mapping = {"Tmrt_2023_189_1200D": "12", "Tmrt_2023_189_1500D": "15", "Tmrt_2023_189_1800D": "18"}

    # Verify base folder
    base_folder = os.path.join(main_folder, base_run)
    if not os.path.exists(base_folder):
        raise FileNotFoundError(f"Base run folder '{base_run}' not found in {main_folder}")

    # Extract BBX from the base run's first file
    ref_file = os.path.join(base_folder, f"{time_keys[0]}.tif")
    base_data, base_metadata = read_raster(ref_file)
    bbx = get_bbx_with_edge_buffer(base_metadata, edge_buffer)

    # Prepare output folder
    os.makedirs(output_folder, exist_ok=True)

    # Loop through all runs
    for subfolder in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder)
        if not os.path.isdir(subfolder_path) or subfolder == base_run:
            continue  # Skip non-folders and base run itself

        print(f"Processing differences for run: {subfolder}")
        output_subfolder = os.path.join(output_folder, subfolder)
        os.makedirs(output_subfolder, exist_ok=True)

        # Process each time of day
        for time_key, time_short in time_mapping.items():
            base_file_path = os.path.join(base_folder, f"{time_key}.tif")
            compare_file_path = os.path.join(subfolder_path, f"{time_key}.tif")

            # Skip if files are missing
            if not os.path.exists(base_file_path) or not os.path.exists(compare_file_path):
                print(f"Missing file for {time_key} in {subfolder}, skipping...")
                continue

            # Read and crop base raster
            base_data, base_metadata = read_raster(base_file_path)
            base_cropped, base_cropped_meta = crop_to_bbx(base_data, base_metadata, bbx)

            # Read and crop comparison raster
            compare_data, compare_metadata = read_raster(compare_file_path)
            compare_cropped, compare_cropped_meta = crop_to_bbx(compare_data, compare_metadata, bbx)

            # Align comparison raster to match base raster
            compare_aligned = align_raster(compare_cropped, compare_cropped_meta, base_cropped, base_cropped_meta)

            # Calculate difference
            difference = compare_aligned - base_cropped

            # Save difference map
            output_path = os.path.join(output_subfolder, f"difference_{time_short}.tif")
            save_difference_raster(difference, base_cropped_meta, output_path)
            print(f"Saved difference map to {output_path}")


def resample_continuous_raster(input_raster, output_raster, target_resolution, method="bilinear"):
    """
    Resample a raster with continuous values using appropriate methods.

    Parameters:
        input_raster (str): Path to the input raster file.
        output_raster (str): Path to save the resampled raster.
        target_resolution (int): Target resolution in meters (e.g., 10, 25).
        method (str): Resampling method ('bilinear', 'average').

    Returns:
        None
    """
    resampling_methods = {
        "bilinear": Resampling.bilinear,
        "average": Resampling.average,
    }

    if method not in resampling_methods:
        raise ValueError(f"Unsupported method: {method}. Use 'bilinear' or 'average'.")

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


def batch_resample_tmrt_maps(diff_folder, aggr_folder, resolutions, methods):
    """
    Batch process resampling for all Tmrt difference maps in subfolders.

    Parameters:
        diff_folder (str): Path to the folder containing subfolders with difference maps.
        aggr_folder (str): Path to save the resampled aggregated maps.
        resolutions (list): List of target resolutions (e.g., [10, 25]).
        methods (list): List of resampling methods (e.g., ['bilinear', 'average']).

    Returns:
        None
    """
    # Ensure the aggregation folder exists
    os.makedirs(aggr_folder, exist_ok=True)

    for subfolder in os.listdir(diff_folder):
        subfolder_path = os.path.join(diff_folder, subfolder)
        if not os.path.isdir(subfolder_path):
            continue

        for time_of_day in ["difference_12.tif", "difference_15.tif", "difference_18.tif"]:
            input_raster = os.path.join(subfolder_path, time_of_day)

            if os.path.exists(input_raster):
                for resolution in resolutions:
                    for method in methods:
                        # Create directories for each method and resolution
                        method_folder = os.path.join(aggr_folder, method)
                        os.makedirs(method_folder, exist_ok=True)
                        resampled_subfolder = os.path.join(method_folder, subfolder)
                        os.makedirs(resampled_subfolder, exist_ok=True)

                        # Define the output path for the resampled raster
                        output_raster = os.path.join(
                            resampled_subfolder, f"{time_of_day.split('.')[0]}_{resolution}m.tif"
                        )

                        # Resample raster
                        resample_continuous_raster(input_raster, output_raster, resolution, method=method)

                        print(f"Resampled raster saved to {output_raster} using {method} method.")


if __name__ == "__main__":
    main_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results"  # Folder with subfolders for Tmrt maps
    diff_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_tmrt_compare"  # Folder containing subfolders with Tmrt difference maps
    aggr_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_tmrt_aggr"
    base_run = "aoi1_all_local_auto"  # Base run for difference calculation
    edge_buffer = 500  # Buffer distance in meters
    resolutions = [5, 10, 15, 25, 30]  # Resolutions in meters for resampling
    methods = ["bilinear", "average"]  # Resampling methods

    # Overlay and calculate differences
    overlay_and_calculate_difference_tmrt(main_folder, diff_folder, base_run, edge_buffer)

    # Resample difference maps
    batch_resample_tmrt_maps(diff_folder, aggr_folder, resolutions, methods)
