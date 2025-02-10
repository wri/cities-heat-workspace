import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np

def reproject_tif(input_tif, output_tif, target_crs):
    """
    Reprojects a TIFF file to the specified CRS and sets NoData values to 0.

    Parameters:
        input_tif (str): Path to the input TIFF file.
        output_tif (str): Path to the output reprojected TIFF file.
        target_crs (str or dict): The target coordinate reference system (e.g., "EPSG:28992").

    Returns:
        None
    """
    # Open the source raster
    with rasterio.open(input_tif) as src:
        # Calculate the transformation and new shape
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )

        # Define metadata for the output file
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height,
            'nodata': None  # Remove NoData so we can manually set 0
        })

        # Create output raster and reproject
        with rasterio.open(output_tif, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):  # Iterate over bands
                # Create empty array for the reprojected data
                dst_array = np.zeros((height, width), dtype=src.dtypes[i - 1])

                # Perform reprojecting
                reproject(
                    source=rasterio.band(src, i),
                    destination=dst_array,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest
                )

                # Convert any remaining NaN values to 0
                dst_array[np.isnan(dst_array)] = 0

                # Write the processed band to the new TIFF
                dst.write(dst_array, i)

    print(f"Reprojected TIFF saved to: {output_tif}")

# Example usage:
reproject_tif(r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\aoi2\aoi2_tree.tif", r"C:\Users\www\WRI-cif\Amsterdam\Laz_result\aoi2\aoi2_tree_32631.tif", "EPSG:32631")
