import rasterio

with rasterio.open(r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\aoi2\aoi2_tree_32631.tif") as src:
    print(src.crs)  # Check if it is None


# Open your raster file
with rasterio.open("your_raster.tif") as src:
    # Get the transform (contains resolution)
    transform = src.transform
    res_x = int(abs(transform.a))  # Convert X resolution to integer
    res_y = int(abs(transform.e))  # Convert Y resolution to integer

    print(f"Raster resolution: {res_x} x {res_y}")
