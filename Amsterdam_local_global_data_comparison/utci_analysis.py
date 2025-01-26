import os
import numpy as np
import pandas as pd
import rasterio
from shade_area_calculation import read_raster
from tmrt_maps_agg import align_raster, save_difference_raster, resample_continuous_raster

def align_to_common_area(source_data, source_meta, target_data, target_meta):
    """
    Clip both rasters to their common area and align their sizes for comparison.

    Parameters:
        source_data (numpy.ndarray): Source raster data.
        source_meta (dict): Metadata of the source raster.
        target_data (numpy.ndarray): Target raster data.
        target_meta (dict): Metadata of the target raster.

    Returns:
        tuple: (aligned_source, aligned_target)
    """
    from rasterio.windows import from_bounds
    from rasterio.warp import reproject, Resampling

    # Calculate bounds for both rasters
    source_bounds = (
        source_meta['transform'][2],  # min_x
        source_meta['transform'][5] + source_meta['height'] * source_meta['transform'][4],  # min_y
        source_meta['transform'][2] + source_meta['width'] * source_meta['transform'][0],  # max_x
        source_meta['transform'][5],  # max_y
    )
    target_bounds = (
        target_meta['transform'][2],  # min_x
        target_meta['transform'][5] + target_meta['height'] * target_meta['transform'][4],  # min_y
        target_meta['transform'][2] + target_meta['width'] * target_meta['transform'][0],  # max_x
        target_meta['transform'][5],  # max_y
    )

    # Find the common area (intersection of bounds)
    common_bounds = (
        max(source_bounds[0], target_bounds[0]),  # max of min_x
        max(source_bounds[1], target_bounds[1]),  # max of min_y
        min(source_bounds[2], target_bounds[2]),  # min of max_x
        min(source_bounds[3], target_bounds[3]),  # min of max_y
    )

    # Validate the common area
    if common_bounds[0] >= common_bounds[2] or common_bounds[1] >= common_bounds[3]:
        raise ValueError("No overlapping area found between source and target rasters.")

    # Clip both rasters to the common area
    source_window = from_bounds(*common_bounds, transform=source_meta['transform'])
    target_window = from_bounds(*common_bounds, transform=target_meta['transform'])

    source_clipped = source_data[
        int(source_window.row_off): int(source_window.row_off + source_window.height),
        int(source_window.col_off): int(source_window.col_off + source_window.width),
    ]
    target_clipped = target_data[
        int(target_window.row_off): int(target_window.row_off + target_window.height),
        int(target_window.col_off): int(target_window.col_off + target_window.width),
    ]

    # Align the clipped rasters to ensure identical dimensions
    aligned_source = np.empty_like(target_clipped, dtype=source_clipped.dtype)
    aligned_target = np.empty_like(target_clipped, dtype=target_clipped.dtype)

    reproject(
        source=source_clipped,
        destination=aligned_source,
        src_transform=source_meta['transform'],
        src_crs=source_meta['crs'],
        dst_transform=target_meta['transform'],
        dst_crs=target_meta['crs'],
        resampling=Resampling.nearest
    )

    reproject(
        source=target_clipped,
        destination=aligned_target,
        src_transform=target_meta['transform'],
        src_crs=target_meta['crs'],
        dst_transform=target_meta['transform'],
        dst_crs=target_meta['crs'],
        resampling=Resampling.nearest
    )

    return aligned_source, aligned_target


def overlay_and_calculate_difference_utci(main_folder, output_folder, base_run):
    """
    Overlay UTCI maps, calculate differences with a base run, and save difference maps as TIFF files.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with UTCI maps.
        output_folder (str): Path to save the difference maps.
        base_run (str): Subfolder name to be used as the base run.

    Returns:
        None
    """
    # Keys to locate time-of-day UTCI maps
    time_keys = ["UTCI_12", "UTCI_15", "UTCI_18"]

    # Verify base folder
    base_folder = os.path.join(main_folder, base_run)
    if not os.path.exists(base_folder):
        raise FileNotFoundError(f"Base run folder '{base_run}' not found in {main_folder}")

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
        for time_key in time_keys:
            base_file_path = os.path.join(base_folder, f"{time_key}.tif")
            compare_file_path = os.path.join(subfolder_path, f"{time_key}.tif")

            # Skip if files are missing
            if not os.path.exists(base_file_path) or not os.path.exists(compare_file_path):
                print(f"Missing file for {time_key} in {subfolder}, skipping...")
                continue

            # Read base raster
            base_data, base_metadata = read_raster(base_file_path)

            # Read comparison raster
            compare_data, compare_metadata = read_raster(compare_file_path)

            # Align comparison raster to match base raster
            compare_aligned = align_raster(compare_data, compare_metadata, base_data, base_metadata)

            # Calculate difference
            difference = compare_aligned - base_data

            # Save difference map
            output_path = os.path.join(output_subfolder, f"difference_{time_key.split('_')[-1]}.tif")
            save_difference_raster(difference, base_metadata, output_path)
            print(f"Saved difference map to {output_path}")


main_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_utci"  # Folder containing all runs
output_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_utci_diff"  # Folder to save difference maps
base_run = "aoi1_all_local_auto"
overlay_and_calculate_difference_utci(main_folder, output_folder, base_run)


def batch_resample_utci_maps(diff_folder, aggr_folder, resolutions, methods):
    """
    Batch process resampling for all UTCI difference maps in subfolders.

    Parameters:
        diff_folder (str): Path to the folder containing subfolders with difference maps.
        aggr_folder (str): Path to save the resampled aggregated maps.
        resolutions (list): List of target resolutions (e.g., [10, 25]).
        methods (list): List of resampling methods (e.g., ['bilinear', 'average']).

    Returns:
        None
    """
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
                        method_folder = os.path.join(aggr_folder, method)
                        os.makedirs(method_folder, exist_ok=True)
                        resampled_subfolder = os.path.join(method_folder, subfolder)
                        os.makedirs(resampled_subfolder, exist_ok=True)

                        output_raster = os.path.join(
                            resampled_subfolder, f"{time_of_day.split('.')[0]}_{resolution}m.tif"
                        )

                        resample_continuous_raster(input_raster, output_raster, resolution, method=method)
                        print(f"Resampled raster saved to {output_raster} using {method} method.")



def calculate_utci_statistics(data):
    """
    Calculate statistical metrics for a UTCI layer.

    Parameters:
        data (numpy.ndarray): Raster data array.

    Returns:
        dict: Statistics including min, max, mean, median, std, and range.
    """
    stats = {
        "min_value": np.min(data),
        "max_value": np.max(data),
        "mean_value": np.mean(data),
        "median_value": np.median(data),
        "std_dev": np.std(data),
        "range": np.max(data) - np.min(data),
    }
    return stats


def process_utci_maps(main_folder, output_excel, baseline_subfolder=None):
    """
    Process UTCI maps from subfolders, analyze numerical statistics, and save the results to an Excel file.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with UTCI maps.
        output_excel (str): Path to save the Excel file with results.
        baseline_subfolder (str, optional): Subfolder name to use as a baseline for comparison.

    Returns:
        None
    """
    # Define mapping for time of day
    time_keys = ["UTCI_12", "UTCI_15", "UTCI_18"]
    results = []

    for subfolder in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder)
        if os.path.isdir(subfolder_path):  # Ensure it's a subfolder
            print(f"Processing statistics for run: {subfolder}")

            # Process UTCI maps for each time of day
            for time_key in time_keys:
                file_path = os.path.join(subfolder_path, f"{time_key}.tif")
                if os.path.exists(file_path):
                    # Read the raster
                    data, metadata = read_raster(file_path)

                    # Calculate numerical statistics
                    utci_stats = calculate_utci_statistics(data)
                    utci_stats["run_name"] = f"{subfolder}_{time_key.split('_')[-1]}"  # Add run name

                    # Append results
                    results.append(utci_stats)

    # Save all results to Excel
    save_results_to_excel(output_excel, results)


def save_results_to_excel(file_path, results):
    """
    Save or update UTCI analysis results in an Excel file with formatting.

    Parameters:
        file_path (str): Path to the Excel file.
        results (list of dict): List of statistics for each map.

    Returns:
        None
    """
    df = pd.DataFrame(results)

    # Ensure `run_name` is the first column
    if "run_name" not in df.columns:
        raise KeyError("'run_name' is missing from the results.")

    df = df[['run_name'] + [col for col in df.columns if col != 'run_name']]

    # Save to Excel
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path)
        df = pd.concat([existing_data, df], ignore_index=True)

    df.to_excel(file_path, index=False)
    print(f"Results successfully saved to {file_path}")


# main_folder = "path_to_utci_data"
# output_excel = "path_to_output_stats.xlsx"
# process_utci_maps(main_folder, output_excel)