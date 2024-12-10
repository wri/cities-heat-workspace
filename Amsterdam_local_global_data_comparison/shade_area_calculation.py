import rasterio
import numpy as np
from rasterio.windows import Window, from_bounds
import pandas as pd
import os


def read_raster(shade_file_path):

    with rasterio.open(shade_file_path) as src:
        data = src.read(1)  # Read the first band
        metadata = src.meta  # Get the full metadata
    return data, metadata


def get_bbx_with_edge_buffer(metadata, edge_buffer=500):
    """
    Calculate a bounding box (BBX) with a buffer removed from each edge of the raster.

    Parameters:
        metadata (dict): Metadata of the raster file.
        edge_buffer (int): Buffer distance (in meters) to crop from each edge.

    Returns:
        tuple: Cropped bounding box (min_x, min_y, max_x, max_y).
    """
    transform = metadata['transform']
    min_x = transform[2]
    max_y = transform[5]
    pixel_size = transform[0]  # Assuming square pixels
    width, height = metadata['width'], metadata['height']

    max_x = min_x + width * pixel_size
    min_y = max_y - height * pixel_size

    # Calculate the cropped bounding box
    cropped_bbx = (
        min_x + edge_buffer,
        min_y + edge_buffer,
        max_x - edge_buffer,
        max_y - edge_buffer
    )

    print(f"Cropped Bounding Box: {cropped_bbx}")
    return cropped_bbx


def crop_to_bbx(data, metadata, bbx, output_path=None):
    """
    Crop a raster to a given bounding box (BBX), save the cropped file, and return the cropped data and metadata.

    Parameters:
        data (numpy.ndarray): Raster data array.
        metadata (dict): Metadata from the raster file.
        bbx (tuple): Bounding box in the format (min_x, min_y, max_x, max_y).
        output_path (str, optional): Path to save the cropped raster. If None, the cropped raster is not saved.

    Returns:
        tuple: Cropped data (numpy.ndarray), updated metadata (dict).
    """
    # Extract transform from metadata
    transform = metadata['transform']

    # Create a window for the given bounding box
    window = from_bounds(*bbx, transform=transform)

    # Read the cropped data using the window
    cropped_data = data[
        int(window.row_off):int(window.row_off + window.height),
        int(window.col_off):int(window.col_off + window.width)
    ]

    # Update metadata for the cropped raster
    cropped_transform = rasterio.windows.transform(window, transform)
    cropped_metadata = metadata.copy()
    cropped_metadata.update({
        "height": cropped_data.shape[0],
        "width": cropped_data.shape[1],
        "transform": cropped_transform
    })

    # Save the cropped raster if an output path is provided
    if output_path:
        with rasterio.open(output_path, "w", **cropped_metadata) as dst:
            dst.write(cropped_data, 1)
        print(f"Cropped raster saved to {output_path}")

    return cropped_data, cropped_metadata


def calculate_shade_area(data, metadata):
    """
    Analyze a shade layer to separate building shades, tree shades, and no-shade areas.

    Parameters:
        data (numpy.ndarray): Raster data array.
        metadata (dict): Metadata from the raster file.

    Returns:
        dict: Analysis results containing areas for each category.
    """
    # Get resolution from metadata
    resolution = metadata['transform'][0]  # Assuming square pixels

    # Identify categories
    building_shade_area = float(np.sum(data == 0) * (resolution ** 2))  # Pixels with value 0
    no_shade_area = float(np.sum(data == 1) * (resolution ** 2))  # Pixels with value 1
    tree_shade_area = float(np.sum((data > 0) & (data < 1)) * (resolution ** 2))  # Pixels between 0 and 1

    # Return results as a dictionary
    results = {
        "building_shade_area_m2": building_shade_area,
        "tree_shade_area_m2": tree_shade_area,
        "no_shade_area_m2": no_shade_area,
    }

    print(results)
    return results


# def save_results_to_excel(file_path, run_name, results):
#     """
#     Save or update shade analysis results in an Excel file.
#
#     Parameters:
#         file_path (str): Path to the Excel file.
#         run_name (str): Unique identifier for the run.
#         results (dict): Calculated shade areas.
#
#     Returns:
#         None
#     """
#     # Convert results dictionary into a DataFrame row
#     results_df = pd.DataFrame([results], index=[run_name])
#
#     # Check if the file exists
#     if os.path.exists(file_path):
#         # Load existing data
#         existing_data = pd.read_excel(file_path, index_col=0)
#
#         # Update or append results
#         if run_name in existing_data.index:
#             existing_data.update(results_df)
#         else:
#             existing_data = pd.concat([existing_data, results_df])
#     else:
#         # Create a new DataFrame
#         existing_data = results_df
#
#     # Save the updated results to Excel
#     existing_data.to_excel(file_path)
#     print(f"Results successfully saved to {file_path}")

def save_results_to_excel(file_path, results):
    df = pd.DataFrame(results)
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path)
        df = pd.concat([existing_data, df], ignore_index=True)
    df.to_excel(file_path, index=False)
    print(f"Results saved to {file_path}")

#
# def reference_layer_shade (shade_path, csv_path, run_name, output_shade_path):
#     data, metadata = read_raster(shade_path)
#     cropped_data, cropped_metadata, cropped_bbx = crop_edges_and_get_bbx(data, metadata, output_shade_path, edge_buffer=500)
#     result = calculate_shade_area(cropped_data, cropped_metadata)
#     save_results_to_excel(csv_path, run_name, result)


def process_shade_maps(main_folder, output_excel, edge_buffer=500):
    """
    Process shade maps from subfolders, crop them according to a calculated BBX,
    analyze shade areas, and save the results to an Excel file.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with shade maps.
        output_excel (str): Path to save the Excel file with results.
        edge_buffer (int): Buffer distance (in meters) to crop from each edge.

    Returns:
        None
    """
    # Define mapping for time of day
    time_mapping = {
        "Shadow_2023_189_1200D": "12",
        "Shadow_2023_189_1500D": "15",
        "Shadow_2023_189_1800D": "18",
    }

    results = []

    for subfolder in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder)
        if os.path.isdir(subfolder_path):  # Ensure it's a subfolder
            # Reference file for BBX extraction
            ref_file = os.path.join(subfolder_path, "Shadow_2023_189_1200D.tif")
            if not os.path.exists(ref_file):
                print(f"Reference file not found: {ref_file}")
                continue

            data, metadata = read_raster(ref_file)
            bbx = get_bbx_with_edge_buffer(metadata, edge_buffer)

            # Process shade maps for three times of the day
            for time_key, time_short in time_mapping.items():
                file_path = os.path.join(subfolder_path, f"{time_key}.tif")
                if os.path.exists(file_path):
                    # Read and crop the raster
                    data, metadata = read_raster(file_path)
                    cropped_data, cropped_metadata = crop_to_bbx(data, metadata, bbx)

                    # Calculate shade areas
                    shade_areas = calculate_shade_area(cropped_data, cropped_metadata)
                    shade_areas["run_name"] = f"{subfolder}_{time_short}"

                    # Append results
                    results.append(shade_areas)

    # Save all results to Excel
    save_results_to_excel(output_excel, results)


process_shade_maps(
    main_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results",
    output_excel=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\shade_2.xlsx",
    edge_buffer=500
)