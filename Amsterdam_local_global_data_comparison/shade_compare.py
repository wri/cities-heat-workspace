import os
import numpy as np
from rasterio.windows import from_bounds, transform as window_transform
from rasterio.errors import WindowError
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
    Clip and align a source raster to match the dimensions and resolution of a target raster.

    Parameters:
        source_data (numpy.ndarray): Source raster data.
        source_meta (dict): Metadata of the source raster.
        target_data (numpy.ndarray): Target raster data for alignment.
        target_meta (dict): Metadata of the target raster.

    Returns:
        numpy.ndarray: Aligned raster data matching the target's dimensions.
    """
    try:
        # Calculate the intersection of source and target bounds
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

        # Compute the intersection of the two bounding boxes
        intersect_bounds = (
            max(source_bounds[0], target_bounds[0]),  # max of min_x
            max(source_bounds[1], target_bounds[1]),  # max of min_y
            min(source_bounds[2], target_bounds[2]),  # min of max_x
            min(source_bounds[3], target_bounds[3]),  # min of max_y
        )

        # Ensure the intersection is valid
        if intersect_bounds[0] >= intersect_bounds[2] or intersect_bounds[1] >= intersect_bounds[3]:
            raise ValueError("No overlapping area between source and target rasters.")

        # Clip the source raster to the intersection bounds
        window = from_bounds(*intersect_bounds, transform=source_meta['transform'])
        source_clipped = source_data[
            int(window.row_off): int(window.row_off + window.height),
            int(window.col_off): int(window.col_off + window.width),
        ]

        # Update metadata for the clipped raster
        clipped_transform = window_transform(window, source_meta['transform'])
        source_meta_clipped = source_meta.copy()
        source_meta_clipped.update({
            "height": source_clipped.shape[0],
            "width": source_clipped.shape[1],
            "transform": clipped_transform,
        })

        # Align the clipped raster to the target raster
        aligned_data = np.empty_like(target_data)
        reproject(
            source=source_clipped,
            destination=aligned_data,
            src_transform=source_meta_clipped['transform'],
            src_crs=source_meta_clipped['crs'],
            dst_transform=target_meta['transform'],
            dst_crs=target_meta['crs'],
            resampling=Resampling.bilinear,  # Adjust resampling method as needed
        )

        return aligned_data

    except WindowError as e:
        print(f"Error in clipping the raster: {e}")
        print("Bounds likely exceed the source raster's extent.")
        raise

    except ValueError as e:
        print(f"Error: {e}")
        raise


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


# main_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results"  # Folder containing all runs
# output_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_diff_maps"  # Folder to save difference maps
# base_run = "aoi1_all_local_auto"  # Subfolder name of the base run
# edge_buffer = 500  # Buffer distance in meters
#
#
# overlay_and_calculate_difference(main_folder, output_folder, base_run, edge_buffer)