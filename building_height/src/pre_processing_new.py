import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import box

def get_bbx_and_crs(input_aoi_vector):
    '''

    :param input_aoi_vector: can take both geojson or geopackage files
    :return: the bbx and crs of the aoi vector, the project crs will be set to this crs
    '''
    # Load the vector file into a GeoDataFrame
    gdf = gpd.read_file(input_aoi_vector)
    # Extract the total bounding box and CRS
    bbx = gdf.total_bounds  # Returns (minx, miny, maxx, maxy)
    crs = gdf.crs
    return bbx, crs


def reproject_crop_raster(raster_path, bbx, target_crs):
    with rasterio.open(raster_path) as src:
        # Calculate the transform, width, and height for the reprojected raster
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds)

        # Set up metadata for the new raster
        profile = src.profile
        profile.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        # Prepare a window for the cropping area based on the bounding box
        window = from_bounds(*bbx, transform)

        # Reproject and read the data within the window
        cropped_data = src.read(window=window, resampling=Resampling.nearest)
        new_transform = src.window_transform(window)

        return cropped_data, new_transform, src.nodata


def reproject_crop_vector(vector_path, bbx, target_crs):
    # Load the vector data
    gdf = gpd.read_file(vector_path)

    # Reproject the vector data to the target CRS
    gdf = gdf.to_crs(target_crs)

    # Convert bounding box to a shapely box for clipping
    bbox = box(bbx[0], bbx[1], bbx[2], bbx[3])

    # Clip the vector data using the bounding box
    clipped_gdf = gdf.clip(bbox)

    return clipped_gdf


def preprocessing(input_aoi_vector, dsm_raster_path, building_height_vector_path):
    bbx , crs = get_bbx_and_crs(input_aoi_vector)
    cropped_raster, new_transform, nodata = reproject_crop_raster(dsm_raster_path, bbx, crs)
    clipped_gdf = reproject_crop_vector(building_height_vector_path, bbx, crs)

    return cropped_raster, new_transform, nodata, clipped_gdf

#preprocessing('https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/aoi1_data/AOI_l.gpkg',
# 'https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/Lidar_and_derived_data/DSM_2023_patch1.TIF',
# 'https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/Building_height_validation/UTGLOBUS_Amsterdam.gpkg')