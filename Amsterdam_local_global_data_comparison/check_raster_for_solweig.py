import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling, transform_bounds

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
    # Set the origin of the first raster to integer coordinates and define it as the reference
    first_raster_path = input_rasters[0]
    first_output_path = output_rasters[0]
    set_raster_origin_to_integer(first_raster_path, first_output_path)

    # Open the first raster as reference
    with rasterio.open(first_output_path) as ref:
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
                'height': ref_shape[0]
            })

            # Reproject and write each band
            with rasterio.open(dst_path, 'w', **profile) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=ref_transform,
                        dst_crs=ref_crs,
                        resampling=Resampling.nearest
                    )


# Example usage
# input_rasters = [r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_utm_f.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_building_utm_f.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_tree_utm.tif']
# output_rasters = [r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_building_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_tree_i.tif']
# align_rasters(input_rasters, output_rasters)
#

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
raster_layers = [r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_local_dem_building_i.tif', r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_source/aoi2_tree_i.tif']
check_raster_layers(raster_layers)
