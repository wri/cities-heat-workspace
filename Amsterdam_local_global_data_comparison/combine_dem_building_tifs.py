import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from scipy.interpolate import griddata
from rasterio.merge import merge


def align_and_crop_dem_to_building(dem_path, building_path, output_tif_path):
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
        with rasterio.open(output_tif_path, 'w', **profile) as dst:
            dst.write(aligned_dem_data, 1)

    print("DEM aligned and cropped to building layer bounding box.")
    return aligned_dem_data, profile, dem_nodata


def fill_missing_values_with_idw(dem_data, dem_nodata):
    """
    Fill missing values in DEM using Inverse Distance Weighting (IDW) interpolation.
    """
    # Create a mask for missing values using the nodata value from the DEM
    if dem_nodata is not None and dem_nodata != np.nan:
        dem_data = np.where(dem_data == dem_nodata, np.nan, dem_data)

        # Create a mask for missing values (NaN)
    mask = np.isnan(dem_data)

    # Debug: Check mask stats
    print("Mask Stats:")
    print(f"Mask Shape: {mask.shape}, Missing Values Count: {np.sum(mask)}")

    # Get coordinates of known and missing values
    known_y, known_x = np.where(~mask)
    known_values = dem_data[~mask]

    missing_y, missing_x = np.where(mask)

    # Debug: Check coordinates
    print("Known Values Stats:")
    print(f"Known Points Count: {len(known_values)}")
    print(f"Known Points Sample: {known_values[:10]} (if available)")
    print("Missing Values Stats:")
    print(f"Missing Points Count: {len(missing_y)}")

    # Check if there are no missing values
    if len(missing_y) == 0:
        print("No missing values to fill. Returning original DEM.")
        return dem_data

    # Create a grid of all coordinates
    grid_y, grid_x = np.mgrid[0:dem_data.shape[0], 0:dem_data.shape[1]]

    # Perform IDW interpolation for missing values
    try:
        dem_filled = griddata(
            points=(known_x, known_y),
            values=known_values,
            xi=(grid_x, grid_y),
            method='nearest'
        )
    except Exception as e:
        print("Error during IDW interpolation:", e)
        return dem_data

    # Debug: Check if dem_filled contains NaNs
    print("DEM Filled Stats:")
    print(f"Filled DEM NaN Count: {np.isnan(dem_filled).sum()}")

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


def merge_tifs(tif1_path, tif2_path, output_tif_path):
    """
    Merges two GeoTIFF layers into a single output GeoTIFF file using Rasterio.

    :param tif1_path: Path to the first input GeoTIFF.
    :param tif2_path: Path to the second input GeoTIFF.
    :param output_tif_path: Path for the merged output GeoTIFF.
    """
    src_files_to_merge = [rasterio.open(tif1_path), rasterio.open(tif2_path)]

    nodata_value = np.nan
    merged_data, merged_transform = merge(src_files_to_merge, nodata=nodata_value)

    merged_data = merged_data[0]


    # Update metadata for the output file
    out_meta = src_files_to_merge[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": merged_data.shape[0],
        "width": merged_data.shape[1],
        "transform": merged_transform,
        "nodata": nodata_value
    })

    # Write the merged file
    # with rasterio.open(output_tif_path, "w", **out_meta) as dest:
    #     dest.write(merged_data)

    print(f"Merged GeoTIFF saved to {output_tif_path}")
    print("Merged Data Shape:", merged_data.shape)
    print("Merged Data Type:", merged_data.dtype)
    return merged_data, out_meta




# merge_tifs(
#     tif1_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p1.tif",
#     tif2_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p2.tif",
#     output_tif_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_m_aoi2.tif"
# )
# merge_tifs(
#     tif1_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p1.tif",
#     tif2_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p2.tif",
#     output_tif_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_m_aoi2.tif"
# )

# dem1_data, dem1_profile, dem1_nodata = align_and_crop_dem_to_building(r'C:\Users\www\WRI-cif\Amsterdam\DEM_patch1.TIF',r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p1.tif")
# dem2_data, dem2_profile, dem2_nodata = align_and_crop_dem_to_building(r'C:\Users\www\WRI-cif\Amsterdam\2023_M_25EZ1.TIF',r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p2.tif")
#
# merged_data, merged_profile, dem_nodata = merge_aligned_dems(dem1_data, dem1_profile, dem1_nodata, dem2_data, dem2_profile, dem2_nodata)
#
# dem_filled = fill_missing_values_with_idw(merged_data, dem_nodata)
#
#     # Save the filled DEM
#     with rasterio.open(r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p1.tif", 'w', merged_profile) as dst:
#         dst.write(dem_filled, 1)
#     print(f"Filled DEM saved")
#
#     combined_path = combine_dem_and_building(dem_filled, r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_m_aoi2.tif", r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\dem_building_aoi2.tif")

def process_divided_patches(dem1_path, dem2_path, building1_path, building2_path, output_dem_p1, output_dem_p2, output_dem_not_filled, output_filled_path, combined_output_path, building_path):
    """
    Process two DEM patches: align and crop, merge, fill missing values, and combine with building data.

    :param dem1_path: Path to the first DEM patch.
    :param dem2_path: Path to the second DEM patch.
    :param building1_path: Path to the first building layer.
    :param building2_path: Path to the second building layer.
    :param output_filled_path: Path to save the filled DEM output.
    :param combined_output_path: Path to save the combined DEM and building layer.
    """
    # Step 1: Align and crop the DEMs to the respective building layers
    dem1_data, dem1_profile, dem1_nodata = align_and_crop_dem_to_building(dem1_path, building1_path, output_dem_p1)
    dem2_data, dem2_profile, dem2_nodata = align_and_crop_dem_to_building(dem2_path, building2_path, output_dem_p2)

    # Step 2: Merge the aligned DEM patches
    merged_data, merged_profile = merge_tifs(output_dem_p1, output_dem_p2, output_dem_not_filled)

    # Step 3: Fill missing values in the merged DEM using IDW interpolation
    dem_filled = fill_missing_values_with_idw(merged_data, dem1_nodata)

    # Step 4: Save the filled DEM
    with rasterio.open(output_filled_path, 'w', **merged_profile) as dst:
        dst.write(dem_filled, 1)
    print(f"Filled DEM saved to {output_filled_path}")

    # Step 5: Combine the filled DEM with the building data
    combined_path = combine_dem_and_building(dem_filled, building_path, combined_output_path)

    print(f"Combined DEM and building layer saved to {combined_output_path}")

    return combined_path

process_divided_patches(
    dem1_path=r'C:\Users\www\WRI-cif\Amsterdam\DEM_patch1.TIF',
    dem2_path=r'C:\Users\www\WRI-cif\Amsterdam\2023_M_25EZ1.TIF',
    building1_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p1.tif",
    building2_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p2.tif",
    output_dem_p1=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\dem_aoi2_p1.tif",
    output_dem_p2=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\dem_aoi2_p2.tif",
    output_dem_not_filled = r"C:\Users\www\WRI\dontwrite",
    output_filled_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\dem_f_aoi2.tif",
    building_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_m_aoi2.tif",
    combined_output_path=r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\dem_building_aoi2.tif"
)
# # Specify file paths
# dem_path = r'C:\Users\www\WRI-cif\Amsterdam\DEM_patch1.TIF'
# building_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p1.tif"
# filled_dem_output_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\DEM_f_aoi2_p1.tif"
# combined_output_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\DEM_building_aoi2_p1.tif"
#
# dem_path = r'C:\Users\www\WRI-cif\Amsterdam\2023_M_25EZ1.TIF'
# building_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\building_aoi2_p2.tif"
# filled_dem_output_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\DEM_f_aoi2_p2.tif"
# combined_output_path = r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\DEM_building_aoi2_p2.tif"
#
# filled_output, final_output = process_dem_with_building(dem_path, building_path, filled_dem_output_path, combined_output_path)
# print("Processing complete. Filled DEM saved at:", filled_output)
# print("Final combined DEM and building saved at:", final_output)


