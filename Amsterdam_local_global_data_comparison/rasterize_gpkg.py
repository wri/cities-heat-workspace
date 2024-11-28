import rasterio
from rasterio.features import rasterize
import fiona
import numpy as np
import os


def rasterize_gpkg(input_file, output_file, resolution=1):
    """
    Rasterizes a GeoPackage (GPKG) file into a raster file.

    Parameters:
    - input_file (str): Path to the input GPKG file.
    - output_file (str): Path to the output raster file.
    - resolution (float): Resolution of the output raster in the same units as the GPKG (default is 1).

    Returns: rasterized tif file
    """
    # Open the GeoPackage file using Fiona
    with fiona.open(input_file, 'r') as src:
        # Get the bounds of the vector file
        bounds = src.bounds
        crs = src.crs
        shapes = [(feature['geometry'], 1) for feature in src]  # Create a list of (geometry, value)

    # Define the transform and shape of the raster
    width = int((bounds[2] - bounds[0]) / resolution)
    height = int((bounds[3] - bounds[1]) / resolution)
    transform = rasterio.transform.from_origin(bounds[0], bounds[3], resolution, resolution)

    # Rasterize the vector data into a numpy array
    raster = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,
        all_touched=True,
        dtype='uint8'
    )

    # Create the output raster file
    with rasterio.open(
            output_file,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype='uint8',
            crs=crs,
            transform=transform,
    ) as dst:
        dst.write(raster, 1)

    print(f"Rasterization complete. Output saved to {output_file}")

    return output_file


rasterize_gpkg(input_file, output_file)