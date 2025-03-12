import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
import geopandas as gpd
import numpy as np
import fiona
import pyproj

import os

# os.environ["PROJ_LIB"] = r"C:\Users\www\PycharmProjects\Amsterdam_ctcm\venv\Lib\site-packages\rasterio\proj_data"

print(os.environ.get('PROJ_LIB'))


def rasterize_gpkg(input_file, output_file, aoi_file, resolution=1, value_column="height"):
    """
    Preprocesses and rasterizes a GeoPackage (GPKG) file into a raster file.

    Parameters:
    - input_file (str): Path to the input GPKG file.
    - output_file (str): Path to the output raster file.
    - aoi_file (str): Path to the AOI GPKG file for cropping and CRS transformation.
    - resolution (float): Resolution of the output raster in the same units as the AOI CRS (default is 1).
    - value_column (str): Column name in the GeoPackage whose values will be used for rasterization.

    Returns:
    - str: Path to the rasterized TIFF file.
    """
    # Load the AOI GeoPackage using Geopandas
    aoi_gdf = gpd.read_file(aoi_file)

    if aoi_gdf.empty:
        raise ValueError("The AOI GeoPackage is empty or invalid.")

    # Get the bounding box and CRS of the AOI
    aoi_bounds = aoi_gdf.total_bounds  # [minx, miny, maxx, maxy]
    aoi_crs = aoi_gdf.crs

    # Load the input GeoPackage using Geopandas
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

    # Ensure the value column exists
    if value_column not in cropped_gdf.columns:
        raise ValueError(f"The column '{value_column}' does not exist in the GeoPackage.")

    # Define the raster bounds and dimensions
    minx, miny, maxx, maxy = aoi_bounds
    width = int((maxx - minx) / resolution)
    height = int((maxy - miny) / resolution)
    transform = from_origin(minx, maxy, resolution, resolution)

    # Prepare shapes for rasterization with values from the specified column
    shapes = [
        (geom, value)
        for geom, value in zip(cropped_gdf.geometry, cropped_gdf[value_column])
        if geom is not None
    ]

    # Rasterize the data
    raster = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,  # Background value
        all_touched=True,
        dtype='float32'
    )

    # Write the raster to a GeoTIFF file
    with rasterio.open(
            output_file,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype='float32',
            crs=aoi_crs.to_string(),
            transform=transform,
            nodata=0
    ) as dst:
        dst.write(raster, 1)

    print(f"Rasterization complete. Output saved to {output_file}")

    return output_file

input_gpkg = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\aoi1_overture_height_utm1.geojson"
aoi_gpkg = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS/AOI_1_utm.gpkg"
output_tif = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\overture_building_utm.tif"
resolution = 1

rasterize_gpkg(input_gpkg, output_tif, aoi_gpkg, resolution)


#aoi1: https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/AOI_1_utm.gpkg