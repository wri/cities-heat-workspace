import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pyproj import CRS

from rasterio.enums import Resampling
from rasterio.transform import Affine


def process_las_to_tif(las_file_path, output_tif_path, bbox, classifications=[6], resolution=1):
    with laspy.open(las_file_path) as lasfile:
        las = lasfile.read()

        x = np.array(las.x)
        y = np.array(las.y)
        z = np.array(las.z)
        class_array = np.array(las.classification)

        mask_bbox = (x >= bbox[0]) & (x <= bbox[2]) & (y >= bbox[1]) & (y <= bbox[3])
        mask_class = np.isin(class_array, classifications)
        mask = mask_bbox & mask_class

        filtered_x = x[mask]
        filtered_y = y[mask]
        filtered_z = z[mask]

        if filtered_x.size == 0:
            print("No points match the specified criteria.")
            return

        min_x, max_x = np.min(filtered_x), np.max(filtered_x)
        min_y, max_y = np.min(filtered_y), np.max(filtered_y)

        # Expand the max bounds slightly to ensure covering the edge case
        max_x += resolution / 2
        max_y += resolution / 2

        width = int((max_x - min_x) // resolution)
        height = int((max_y - min_y) // resolution)

        grid = np.full((height, width), np.nan, dtype=np.float32)

        for x, y, z in zip(filtered_x, filtered_y, filtered_z):
            col = int((x - min_x) // resolution)
            row = int((max_y - y) // resolution)

            # Ensure that the indices are within the array bounds
            if row >= height:
                row = height - 1
            if col >= width:
                col = width - 1

            grid[row, col] = max(grid[row, col], z) if not np.isnan(grid[row, col]) else z

        transform = from_origin(min_x, max_y, resolution, -resolution)

        with rasterio.open(
                output_tif_path, 'w', driver='GTiff',
                height=height, width=width,
                count=1, dtype=str(grid.dtype),
                crs=CRS.from_epsg(28992).to_wkt(),
                transform=transform
        ) as dst:
            dst.write(grid, 1)



# Example usage
las_file_path = r'C:\Users\www\WRI-cif\Amsterdam\2023_C_25GN1.LAZ'
output_tif_path = r'C:\Users\www\WRI-cif\Validation_height\lidartoras\building&ground2.tif'

bbox = [120764.46, 483845.95, 122764.46, 485845.95]

# process_las_to_tif(las_file_path, output_tif_path, bbox)


# Open the input raster
input_path = r'C:\Users\www\WRI-cif\Validation_height\lidartoras\building_test1.tif'
output_path = r'C:\Users\www\WRI-cif\Validation_height\lidartoras\building_i.tif'

with rasterio.open(input_path) as src:
    # Read the raster data
    data = src.read(1)

    # Invert the y-axis in the transform
    new_transform = Affine(src.transform.a, src.transform.b, src.transform.c,
                           src.transform.d, -src.transform.e,
                           src.transform.f + (src.height * src.transform.e))

    # Save the corrected raster
    profile = src.profile
    profile.update(transform=new_transform)

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data, 1)

print("Y-axis inverted successfully and saved to", output_path)
