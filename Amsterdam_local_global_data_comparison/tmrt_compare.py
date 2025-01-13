import os
import pandas as pd
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from shade_area_calculation import read_raster, get_bbx_with_edge_buffer, crop_to_bbx


def calculate_tmrt_statistics(data):
    """
    Calculate statistical metrics for a Tmrt layer.

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


def process_tmrt_maps(main_folder, output_excel, edge_buffer=500, baseline_subfolder=None):
    """
    Process Tmrt maps from subfolders, crop them according to a calculated BBX,
    analyze numerical statistics, and save the results to an Excel file.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with Tmrt maps.
        output_excel (str): Path to save the Excel file with results.
        edge_buffer (int): Buffer distance (in meters) to crop from each edge.
        baseline_subfolder (str, optional): Subfolder name to use as a baseline for comparison.

    Returns:
        None
    """
    # Define mapping for time of day
    time_mapping = {
        "Tmrt_2023_189_1200D": "12",
        "Tmrt_2023_189_1500D": "15",
        "Tmrt_2023_189_1800D": "18",
    }

    results = []

    for subfolder in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder)
        if os.path.isdir(subfolder_path):  # Ensure it's a subfolder
            # Reference file for BBX extraction
            ref_file = os.path.join(subfolder_path, "Tmrt_2023_189_1200D.tif")
            if not os.path.exists(ref_file):
                print(f"Reference file not found: {ref_file}")
                continue

            data, metadata = read_raster(ref_file)
            bbx = get_bbx_with_edge_buffer(metadata, edge_buffer)

            # Process Tmrt maps for three times of the day
            for time_key, time_short in time_mapping.items():
                file_path = os.path.join(subfolder_path, f"{time_key}.tif")
                if os.path.exists(file_path):
                    # Read and crop the raster
                    data, metadata = read_raster(file_path)
                    cropped_data, cropped_metadata = crop_to_bbx(data, metadata, bbx)

                    # Calculate numerical statistics
                    tmrt_stats = calculate_tmrt_statistics(cropped_data)
                    tmrt_stats["run_name"] = f"{subfolder}_{time_short}"  # Ensure 'run_name' is added

                    # Append results
                    results.append(tmrt_stats)

    # Save all results to Excel
    save_results_to_excel(output_excel, results)


def save_results_to_excel(file_path, results):
    """
    Save or update Tmrt analysis results in an Excel file with formatting.

    Parameters:
        file_path (str): Path to the Excel file.
        results (list of dict): List of statistics for each map.

    Returns:
        None
    """
    df = pd.DataFrame(results)

    # Debug: Print the DataFrame columns to verify 'run_name' exists
    print("Columns in DataFrame:", df.columns)

    # Ensure `run_name` is the first column
    if "run_name" not in df.columns:
        raise KeyError("'run_name' is missing from the results.")

    df = df[['run_name'] + [col for col in df.columns if col != 'run_name']]

    # Sort results by time (12, 15, 18)
    df['time'] = df['run_name'].str.extract(r'_(\d+)$').astype(int)
    df = df.sort_values(by='time').drop(columns=['time'])

    # Save to Excel
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path)
        df = pd.concat([existing_data, df], ignore_index=True)

    df.to_excel(file_path, index=False)
    print(f"Results successfully saved to {file_path}")


# Example Usage
if __name__ == "__main__":
    main_folder = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results"  # Folder containing subfolders with Tmrt maps
    output_excel = "tmrt_stats.xlsx"
    edge_buffer = 500

    process_tmrt_maps(main_folder, output_excel, edge_buffer)
