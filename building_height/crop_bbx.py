import geopandas as gpd
import rasterio
from shapely.geometry import Point, box
from rasterio.windows import from_bounds
import numpy as np


def create_2km_bbox(center_x, center_y):
    half_size = 1000  # 1km in each direction for a 2km x 2km bounding box
    xmin = center_x - half_size
    xmax = center_x + half_size
    ymin = center_y - half_size
    ymax = center_y + half_size
    return box(xmin, ymin, xmax, ymax)


# Function to crop the raster to the bounding box
def crop_raster(raster_path, bbox):
    # Open the raster file
    with rasterio.open(raster_path) as src:
        # Get the window corresponding to the bounding box
        window = from_bounds(bbox.bounds[0], bbox.bounds[1], bbox.bounds[2], bbox.bounds[3], src.transform)
        nodata_value = src.nodata

        # Read the cropped raster data
        cropped_data = src.read(1, window=window)

        # Update the transform to match the cropped raster
        transform = src.window_transform(window)

        # Save the cropped raster (optional)
        profile = src.profile
        profile.update({
            "height": cropped_data.shape[0],
            "width": cropped_data.shape[1],
            "transform": transform
        })

        # with rasterio.open(dst_path, 'w', **profile) as dst:
            # dst.write(cropped_data, 1)

    return cropped_data, transform, nodata_value


# Function to crop the vector data to the bounding box
def crop_vector(vector_path, bbox):
    # Load the vector data
    gdf = gpd.read_file(vector_path)

    # Clip the vector data to the bounding box
    clipped_gdf = gpd.clip(gdf, bbox)

    return clipped_gdf


#example_coordinates = 121764.46,484845.95
# List of possible column names representing height


# Function to find the correct height column and print the first 10 heights
# def print_building_heights(cropped_vector_data):
#     found_column = None
#
#     # Search for the first matching column name in the dataframe
#     for column_name in height_column_names:
#         if column_name in cropped_vector_data.columns:
#             found_column = column_name
#             break
#
#     # Print heights if a valid column was found
#     if found_column:
#         print(f"Heights of the first 10 buildings after cropping (from column '{found_column}'):")
#         print(cropped_vector_data[found_column].head(10))
#     else:
#         print("No column representing height found in the geopackage.")

# Example coordinates for the center of the bounding box (EPSG:28992 - Amersfoort / RD New)
# example_coordinates = (121764.46, 484845.95)
#
# # Create a bounding box (2km x 2km)
# bbox = create_2km_bbox(*example_coordinates)
#
# # Path to your geopackage file
# vector_path = r'C:\Users\www\WRI-cif\Validation_height\F-UTGLOBUS_Ams.gpkg'
# raster_path = r'C:\Users\www\WRI-cif\Validation_height\DSM_2023.TIF'
# cropped_vector_data = crop_vector(vector_path, bbox)
# print(cropped_vector_data.columns)

# # Crop the vector data to the bounding box
# cropped_vector_data = crop_vector(vector_path, bbox)
#
# # Try to print the heights of the first 10 buildings
# print_building_heights(cropped_vector_data)

#crop_raster(raster_path,bbox)