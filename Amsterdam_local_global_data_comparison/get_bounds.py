import rasterio
from rasterio.warp import transform as warp_transform  # Import transform for CRS conversion


def get_lat_lon_from_raster(raster_path):
    """
    Extract and print latitude and longitude coordinates (WGS 84) for the extent of a raster.

    Parameters:
        raster_path (str): Path to the raster file.

    Returns:
        dict: Bounding box coordinates in WGS 84 (lat_min, lat_max, lon_min, lon_max).
    """
    with rasterio.open(raster_path) as src:
        # Get CRS and transform
        src_crs = src.crs
        bounds = src.bounds  # Get raster bounds in source CRS

        print(f"Raster Bounds in CRS {src_crs}: {bounds}")

        # Define the corner coordinates
        corners_x = [bounds.left, bounds.right]  # X coordinates (min_x, max_x)
        corners_y = [bounds.bottom, bounds.top]  # Y coordinates (min_y, max_y)

        # Convert corner coordinates to WGS 84
        dst_crs = "EPSG:4326"  # WGS 84
        longitudes, latitudes = warp_transform(
            src_crs, dst_crs,
            corners_x, corners_y
        )

        lat_min, lat_max = min(latitudes), max(latitudes)
        lon_min, lon_max = min(longitudes), max(longitudes)

        print(f"Latitude range: {lat_min:.10f} to {lat_max:.10f}")
        print(f"Longitude range: {lon_min:.10f} to {lon_max:.10f}")

        return {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max
        }




# Example usage
raster_path = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile002\aoi2_global_building_dem.tif"
lat_lon_bounds = get_lat_lon_from_raster(raster_path)