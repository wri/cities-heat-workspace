import numpy as np
import rasterio
from rasterio.enums import Resampling


def fill_nans_in_tif(input_tif, output_tif):
    with rasterio.open(input_tif) as src:
        # Read the data as a numpy array
        data = src.read(1)  # Read the first band

        # Check for NaN values and replace them with 0
        if np.isnan(data).any():
            print("NaN values found, filling with 0...")
            data = np.nan_to_num(data, nan=0)

        # Get the current nodata value
        nodata_value = src.nodata

        if nodata_value is not None:
            print(f"Current nodata value: {nodata_value}")
            # Replace nodata values with -9999
            data[data == nodata_value] = -9999
            print("Replaced nodata values with -9999.")
        else:
            print("No nodata value found in the file.")

        # Copy the metadata and update the nodata value to -9999
        metadata = src.meta
        metadata.update(nodata=-9999)

        # Write the modified data to a new TIFF file
        with rasterio.open(output_tif, 'w', **metadata) as dst:
            dst.write(data, 1)
        print(f"Output saved to {output_tif}")


# Usage example
input_tif = r'C:\Users\www\WRI-cif\Amsterdam\aoi1_tree_height.tif'
output_tif = r'C:\Users\www\WRI-cif\Amsterdam\aoi1_tree_height_1.tif'
fill_nans_in_tif(input_tif, output_tif)