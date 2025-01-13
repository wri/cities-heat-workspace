import os
import numpy as np
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
import rasterio
from shade_area_calculation import read_raster, get_bbx_with_edge_buffer, crop_to_bbx


def overlay_and_calculate_difference(main_folder, output_folder, base_run, edge_buffer=500):
    """
    Overlay shade maps, calculate differences with a base run, and save difference maps as TIFF files.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with shade maps.
        output_folder (str): Path to save the difference maps.
        base_run (str): Subfolder name to be used as the base run.
        edge_buffer (int): Buffer distance (in meters) to crop from each edge.

    Returns:
        None
    """
    # Keys to locate time-of-day shade maps
    time_keys = ["Shadow_2023_189_1200D", "Shadow_2023_189_1500D", "Shadow_2023_189_1800D"]
    time_mapping = {"Shadow_2023_189_1200D": "12", "Shadow_2023_189_1500D": "15", "Shadow_2023_189_1800D": "18"}

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


def align_raster(source_data, source_meta, target_data, target_meta):
    """
    Align a raster to match the dimensions and resolution of a target raster.

    Parameters:
        source_data (numpy.ndarray): Source raster data.
        source_meta (dict): Metadata of the source raster.
        target_data (numpy.ndarray): Target raster data for alignment.
        target_meta (dict): Metadata of the target raster.

    Returns:
        numpy.ndarray: Aligned raster data matching the target's dimensions.
    """
    aligned_data = np.empty_like(target_data)

    reproject(
        source=source_data,
        destination=aligned_data,
        src_transform=source_meta['transform'],
        src_crs=source_meta['crs'],
        dst_transform=target_meta['transform'],
        dst_crs=target_meta['crs'],
        resampling=Resampling.nearest
    )
    return aligned_data


def save_difference_raster(data, metadata, output_path):
    """
    Save a difference raster to a TIFF file.

    Parameters:
        data (numpy.ndarray): Difference raster data.
        metadata (dict): Metadata for the raster file.
        output_path (str): Path to save the difference raster.
    """
    metadata.update(dtype='float32', nodata=None)  # Update metadata for difference layer
    with rasterio.open(output_path, 'w', **metadata) as dst:
        dst.write(data.astype('float32'), 1)
    print(f"Difference raster saved: {output_path}")


main_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results"  # Folder containing all runs
output_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_diff_maps"  # Folder to save difference maps
base_run = "aoi1_all_local_auto"  # Subfolder name of the base run
edge_buffer = 500  # Buffer distance in meters


overlay_and_calculate_difference(main_folder, output_folder, base_run, edge_buffer)