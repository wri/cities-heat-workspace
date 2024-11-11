import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from scipy.interpolate import griddata


def align_and_crop_dem_to_building(dem_path, building_path):
    """
    Align and crop DEM to the bounding box and resolution of the building layer.
    """
    with rasterio.open(building_path) as building:
        building_bounds = building.bounds
        building_transform = building.transform
        building_shape = (building.height, building.width)
        building_profile = building.profile

    with rasterio.open(dem_path) as dem:
        # Read the nodata value from the DEM
        dem_nodata = dem.nodata

        # Calculate the transformation and resampling for the DEM to match the building
        transform, width, height = calculate_default_transform(
            dem.crs, building_profile['crs'], building_shape[1], building_shape[0],
            *building_bounds
        )

        # Define a new profile with updated transform and size
        profile = dem.profile
        profile.update({
            'transform': transform,
            'width': width,
            'height': height
        })

        # Resample and crop the DEM to match the building extent
        aligned_dem_data = np.empty((height, width), dtype=dem.profile['dtype'])
        reproject(
            source=rasterio.band(dem, 1),
            destination=aligned_dem_data,
            src_transform=dem.transform,
            src_crs=dem.crs,
            dst_transform=transform,
            dst_crs=building_profile['crs'],
            resampling=Resampling.bilinear
        )

    print("DEM aligned and cropped to building layer bounding box.")
    return aligned_dem_data, profile, dem_nodata


def fill_missing_values_with_idw(dem_data, dem_nodata):
    """
    Fill missing values in DEM using Inverse Distance Weighting (IDW) interpolation.
    """
    # Create a mask for missing values using the nodata value from the DEM
    mask = dem_data == dem_nodata

    # Get coordinates of known and missing values
    known_y, known_x = np.where(~mask)
    known_values = dem_data[~mask]

    # Create a grid of all coordinates
    grid_y, grid_x = np.mgrid[0:dem_data.shape[0], 0:dem_data.shape[1]]

    # Perform IDW interpolation for missing values
    dem_filled = griddata(
        points=(known_x, known_y),
        values=known_values,
        xi=(grid_x, grid_y),
        method='nearest'
    )

    print("Missing values in DEM filled with IDW interpolation.")
    return dem_filled


def combine_dem_and_building(dem_filled, building_path, output_path):
    """
    Add building heights on top of the DEM.
    """
    with rasterio.open(building_path) as building:
        building_data = building.read(1)
        profile = building.profile  # Move profile access within the 'with' block

    # Combine DEM and building layers, giving preference to building data
    combined_dem = np.where(building_data > 0, dem_filled + building_data, dem_filled)

    # Save combined DEM + building layer
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(combined_dem, 1)

    print(f"Combined DEM and building layers saved to {output_path}")
    return output_path


# Main processing function
def process_dem_with_building(dem_path, building_path, filled_dem_output_path, combined_output_path):
    dem_aligned, profile, dem_nodata = align_and_crop_dem_to_building(dem_path, building_path)
    dem_filled = fill_missing_values_with_idw(dem_aligned, dem_nodata)

    # Save the filled DEM
    with rasterio.open(filled_dem_output_path, 'w', **profile) as dst:
        dst.write(dem_filled, 1)
    print(f"Filled DEM saved to {filled_dem_output_path}")

    combined_path = combine_dem_and_building(dem_filled, building_path, combined_output_path)
    return filled_dem_output_path, combined_path


# Specify file paths
dem_path = r'C:\Users\www\WRI-cif\Amsterdam\DEM_patch1.tif'
building_path = r'C:\Users\www\WRI-cif\Validation_height\lidartoras\building_i.tif'
filled_dem_output_path = r'C:\Users\www\WRI-cif\Validation_height\lidartoras\filled_DEM.tif'
combined_output_path = r'C:\Users\www\WRI-cif\Validation_height\lidartoras\filled_DEM&building.tif'

filled_output, final_output = process_dem_with_building(dem_path, building_path, filled_dem_output_path, combined_output_path)
print("Processing complete. Filled DEM saved at:", filled_output)
print("Final combined DEM and building saved at:", final_output)


