import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling, transform_bounds

import rasterio
import numpy as np

def fill_and_set_nodata(raster_path, output_path, fill_value=0, new_nodata=-9999):
    with rasterio.open(raster_path) as src:
        # Read the data and nodata value from the source raster
        nodata = src.nodata
        data = src.read(1, masked=True)  # Read the first band data as masked array

        # Fill the nodata areas with the specified fill_value
        if nodata is not None:
            data = np.where(data.mask, fill_value, data)  # Fill original nodata with fill_value

        # More aggressive edge handling to remove nodata values
        # Fill additional rows and columns around the edge if necessary
        data[:, 0:2] = fill_value  # Fill the first two columns
        data[:, -2:] = fill_value  # Fill the last two columns
        data[0:2, :] = fill_value  # Fill the first two rows
        data[-2:, :] = fill_value  # Fill the last two rows

        # Update the profile to change the nodata value
        profile = src.profile
        profile['nodata'] = new_nodata
        profile['transform'] = src.transform
        profile['width'] = data.shape[1]
        profile['height'] = data.shape[0]

        # Write the updated data to a new raster file
        with rasterio.open(output_path, 'w', **profile) as dst:
            # Replace old nodata with new nodata in the data array
            data = np.where(data == nodata, new_nodata, data)
            dst.write(data, 1)  # Write data back to disk




# Example usage
# input_raster = r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem.tif'
# output_raster = r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_test.tif'
# fill_and_set_nodata(input_raster, output_raster)

def set_raster_origin_to_integer(raster_path, output_path):
    with rasterio.open(raster_path) as src:
        # Read the original affine transform
        transform = src.transform

        # Create a new transform with rounded origin coordinates
        new_transform = Affine(transform.a, transform.b, round(transform.c),
                               transform.d, transform.e, round(transform.f))

        # Update profile with new transform
        profile = src.profile
        profile['transform'] = new_transform

        # Write the updated raster to a new file
        with rasterio.open(output_path, 'w', **profile) as dst:
            for i in range(1, src.count + 1):
                data = src.read(i)
                dst.write(data, i)


def align_rasters(input_rasters, output_rasters):
    # Open the first raster as the reference but do not change or output it
    with rasterio.open(input_rasters[0]) as ref:
        ref_transform = ref.transform
        ref_crs = ref.crs
        ref_shape = (ref.height, ref.width)

    # Process each subsequent raster
    for src_path, dst_path in zip(input_rasters[1:], output_rasters[1:]):
        with rasterio.open(src_path) as src:
            # Update profile for the output raster to match the reference
            profile = src.profile
            profile.update({
                'crs': ref_crs,
                'transform': ref_transform,
                'width': ref_shape[1],
                'height': ref_shape[0],
                'dtype': src.dtypes[0]  # Ensure dtype matches
            })

            # Reproject and write each band
            with rasterio.open(dst_path, 'w', **profile) as dst:
                for i in range(1, src.count + 1):
                    # Create an empty array for the destination data
                    dest_array = np.empty((ref_shape[0], ref_shape[1]), dtype=src.dtypes[0])

                    reproject(
                        source=rasterio.band(src, i),
                        destination=dest_array,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=ref_transform,
                        dst_crs=ref_crs,
                        resampling=Resampling.nearest
                    )

                    # Write the reprojected data to the output raster
                    dst.write(dest_array, indexes=i)




def check_raster_layers(layers):
    reference_crs = None
    reference_transform = None
    reference_extent = None

    for layer in layers:
        with rasterio.open(layer) as src:
            # Check CRS
            if reference_crs is None:
                reference_crs = src.crs
                print(f"{layer}: CRS set to {src.crs}")
            elif src.crs != reference_crs:
                print(f"CRS mismatch in {layer}: {src.crs} does not match {reference_crs}")
                continue
            else:
                print(f"{layer}: CRS matches the reference CRS {reference_crs}")

            # Check resolution
            res_x, res_y = src.res
            print(res_x,res_y)
            if res_x != 1 or res_y != 1:
                print(f"Resolution issue in {layer}: found resolution ({res_x}, {res_y}), expected (1, 1)")
                continue

            # Calculate and check extent and integer origin
            extent = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
            origin_x, origin_y = src.transform.c, src.transform.f
            if not origin_x.is_integer() or not origin_y.is_integer():
                print(f"Origin issue in {layer}: origin ({origin_x}, {origin_y}) are not integers")
                continue

            if reference_extent is None:
                reference_extent = extent
                reference_transform = src.transform
                print(f"{layer}: Extent and transform set to {extent}, origin is integer.")
            elif extent != reference_extent or src.transform != reference_transform:
                print(f"Extent/alignment issue in {layer}: extent {extent} or transform {src.transform} different from reference")
                continue
            else:
                print(f"{layer}: Extent, transform, and origin match the reference. Shape: {src.shape}")

            # If all checks pass, calculate and print the BBX in EPSG:4326
            bbx_4326 = transform_bounds(src.crs, 'EPSG:4326', *extent)
            print(f"{layer}: BBX in EPSG:4326 is {bbx_4326}")


# Example usage
if __name__ == '__main__':
    input_rasters = [r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile001\UTbuilding_AOI1.tif',
                     r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile001\UTbuilding_NASADEM_AOI1.tif',
                     r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\all-street-trees-90pctl-achievable.tif']
    output_rasters = [None,
                      r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi1_dem.tif',
                      r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi1_street_tree.tif']
    align_rasters(input_rasters, output_rasters)
# Example usage
# raster_layers = [r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_building_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_tree_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source\cif_lulc.tif']
# check_raster_layers(raster_layers)
