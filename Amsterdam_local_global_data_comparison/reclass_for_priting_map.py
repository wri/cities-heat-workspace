import os
import rasterio
from rasterio.enums import Resampling


def reclassify_raster(input_folder, output_folder):
    # Define the bins
    bins = [
        float('-inf'), -4, -2, -1, 0, 1, 2, 4, float('inf')
    ]
    # Define the new values, max of the bin
    new_values = [-4, -2, -1, 0, 1, 2, 4, 10]

    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)

    # Process each file in the input directory
    for filename in os.listdir(input_folder):
        if filename.startswith("difference") and filename.endswith('.tif'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_recl.tif")

            with rasterio.open(input_path) as src:
                data = src.read(1)  # Read the first band

                # Reclassify the data
                reclassified_data = data.copy()
                for i, upper_limit in enumerate(bins[1:]):
                    reclassified_data[(data > bins[i]) & (data <= upper_limit)] = new_values[i]

                # Write the reclassified data to a new file
                with rasterio.open(
                        output_path, 'w',
                        driver='GTiff',
                        height=src.height,
                        width=src.width,
                        count=1,
                        dtype=reclassified_data.dtype,
                        crs=src.crs,
                        transform=src.transform
                ) as dst:
                    dst.write(reclassified_data, 1)
                    dst.update_tags(1, **src.tags(1))  # Copy metadata from the source file

    print("Reclassification complete.")


# Example usage
input_folder = r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_utci_aggr\average\aoi1_all_global'
output_folder = r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\utci_reclass\utci_global_diff_aggr'
reclassify_raster(input_folder, output_folder)
