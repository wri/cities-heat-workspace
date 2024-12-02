import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
import geopandas as gpd
import numpy as np
import fiona
import pyproj

import os

os.environ["PROJ_LIB"] = r"C:\Users\www\PycharmProjects\Amsterdam_ctcm\venv\Lib\site-packages\rasterio\proj_data"

print(os.environ.get('PROJ_LIB'))

def rasterize_gpkg(input_file, output_file, aoi_file, resolution=1):
    """
    Preprocesses and rasterizes a GeoPackage (GPKG) file into a raster file.

    Parameters:
    - input_file (str): Path to the input GPKG file.
    - output_file (str): Path to the output raster file.
    - aoi_file (str): Path to the AOI GPKG file for cropping and CRS transformation.
    - resolution (float): Resolution of the output raster in the same units as the AOI CRS (default is 1).

    Returns:
    - str: Path to the rasterized TIFF file.
    """
    # Load the AOI GeoPackage
    aoi_gdf = gpd.read_file(aoi_file)

    if aoi_gdf.empty:
        raise ValueError("The AOI GeoPackage is empty or invalid.")

    # Get the bounding box and CRS of the AOI
    aoi_bounds = aoi_gdf.total_bounds  # [minx, miny, maxx, maxy]
    aoi_crs = aoi_gdf.crs

    # Load the input GeoPackage
    input_gdf = gpd.read_file(input_file)

    if input_gdf.empty:
        raise ValueError("The input GeoPackage is empty or invalid.")

    # Reproject the input GeoPackage to match the AOI CRS
    if input_gdf.crs != aoi_crs:
        input_gdf = input_gdf.to_crs(aoi_crs)

    # Crop the input GeoPackage to the AOI bounding box
    cropped_gdf = input_gdf.cx[aoi_bounds[0]:aoi_bounds[2], aoi_bounds[1]:aoi_bounds[3]]

    if cropped_gdf.empty:
        raise ValueError("No features remain after cropping to the AOI.")

    # Define the raster bounds and dimensions
    minx, miny, maxx, maxy = aoi_bounds
    width = int((maxx - minx) / resolution)
    height = int((maxy - miny) / resolution)
    transform = from_origin(minx, maxy, resolution, resolution)

    # Prepare shapes for rasterization
    shapes = [(geom, 1) for geom in cropped_gdf.geometry if geom is not None]

    # Rasterize the data
    raster = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,  # Background value
        all_touched=True,
        dtype='uint8'
    )

    # Write the raster to a GeoTIFF file
    with rasterio.open(
            output_file,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype='uint8',
            crs=aoi_crs.to_string(),
            transform=transform,
            nodata=0
    ) as dst:
        dst.write(raster, 1)

    print(f"Rasterization complete. Output saved to {output_file}")

    return output_file

input_gpkg = r"C:\Users\www\WRI-cif\GLOBAL_COM\UT_Amsterdam.gpkg"
aoi_gpkg = r"C:\Users\www\WRI-cif\GLOBAL_COM\AOI_2_utm.gpkg"
output_tif = r"C:\Users\www\WRI-cif\GLOBAL_COM\UT_raster_AOI2.tif"
resolution = 1

rasterize_gpkg(input_gpkg, output_tif, aoi_gpkg, resolution)