import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin


def filter_tree_canopy(input_path, output_path, bbx, amplitude_threshold = 6.7,
                       min_height=2.0, reflectance_threshold=0.3, min_cluster_area=5,
                       eps=1.5, min_samples=5, point_density=1.5):
    """
    Filters and saves vegetation points representing tree canopies from a LAZ file.

    Parameters:
    - input_path: Path to the input LAZ file.
    - output_path: Path where the filtered LAZ file will be saved.
    - bbx: Bounding box as a tuple (min_x, max_x, min_y, max_y).
    - min_height: Minimum height threshold to exclude low vegetation and ground objects.
    - min_cluster_area: Minimum area threshold for clusters to be considered tree canopies.
    - ndvi_threshold: NDVI threshold for vegetation filtering (if NDVI is available).
    - eps: DBSCAN epsilon value for clustering in meters.
    - min_samples: Minimum samples for DBSCAN clustering.
    - point_density: Estimated points per square meter to determine cluster size.
    """
    with laspy.open(input_path) as file:
        las = file.read()

    # Unpack bounding box
    min_x, max_x, min_y, max_y = bbx

    # available_fields = list(las.point_format.dimension_names)
    # attributes_to_check = ['classification', 'Z', 'number_of_returns', 'Reflectance']
    # for attr in attributes_to_check:
    #     if attr in available_fields:
    #         print(f"Attribute '{attr}' is available.")
    #     else:
    #         print(f"Attribute '{attr}' is NOT available.")

    # # Step 1: Crop by Bounding Box (BBX)
    # in_bbx_filter = (las.x >= min_x) & (las.x <= max_x) & (las.y >= min_y) & (las.y <= max_y)
    # bbx_filtered_points = las.points[in_bbx_filter]
    #
    # class_1_filter = (bbx_filtered_points['classification'] == 1)
    # class_1_points = bbx_filtered_points[class_1_filter]
    # print(f"Number of points after class 1 filter: {len(class_1_points)}")
    #
    #
    #     # Step 3: Apply height filter to exclude ground-level objects
    # height_filter = (bbx_filtered_points['Z'] >= 3.5) & (bbx_filtered_points['Z'] <= 40.0)
    # height_filtered_points = bbx_filtered_points[height_filter]
    # print(f"Number of points after height filter: {len(height_filtered_points)}")
    #
    #
    # multi_return_filter = height_filtered_points['number_of_returns'] > 1
    # multi_return_point = height_filtered_points[multi_return_filter]
    # print(f"Number of points after multi-return filter: {multi_return_filter.sum()}")
    #
    # amplitude_filter = multi_return_point['Amplitude'] < amplitude_threshold
    # vegetation_points = multi_return_point[amplitude_filter]
    # print(f"Number of points after amplitude filter (Amplitude < 6.7): {len(vegetation_points)}")


    #     # Step 5: Apply reflectance filter
    # if 'Reflectance' in available_fields:
    #     reflectance_filter = height_filtered_points['Reflectance'] > reflectance_threshold
    #     print(f"Number of points after reflectance filter: {reflectance_filter.sum()}")
    # else:
    #     print("Skipping reflectance filter as the attribute is not available.")
    #     reflectance_filter = np.ones(len(height_filtered_points), dtype=bool)

        # Combine the filters to create a final mask
    # vegetation_mask = multi_return_filter & reflectance_filter

    combined_filter = (
            (las.x >= min_x) & (las.x <= max_x) &  # Bounding box filter
            (las.y >= min_y) & (las.y <= max_y) &
            (las['classification'] == 1) &  # Class 1 (unclassified) filter
            (las.z >= 3.5) &  # Height filter (min)
            (las.z <= 40.0) &  # Height filter (max)
            (las['number_of_returns'] > 1) &  # Multi-return filter
            (las['Amplitude'] < amplitude_threshold)  # Amplitude filter
    )

    # Apply the combined filter
    vegetation_points = las.points[combined_filter]
    print(f"Number of points after applying combined filters: {len(vegetation_points)}")

    # Write the filtered points to a new LAZ file
    with laspy.open(output_path, mode='w', header=las.header) as writer:
        writer.write_points(vegetation_points)

    print(f"Filtered vegetation points saved to {output_path}")


    # Calculate NDVI for class 1 points if NIR and Red bands are available
    # if hasattr(height_filtered_points, 'red') and hasattr(height_filtered_points, 'nir'):
    #     red = class_1_points['red'].astype(float)
    #     nir = class_1_points['nir'].astype(float)
    #
    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         ndvi = (nir - red) / (nir + red)
    #         ndvi[(nir + red) == 0] = 0  # Set NDVI to zero where red + nir is zero
    #     ndvi = np.clip(ndvi, -1, 1)
    #     vegetation_mask = ndvi >= ndvi_threshold
    #
    # else:
    #     print("NDVI data not available in point cloud.")
        # Filtering the points with the NDVI threshold

        #
        # # Filter out first return points from class 1 points
        # first_return_mask_class_1 = class_1_points['return_number'] == 1

        # Combine NDVI and first return masks
        # combined_mask = vegetation_mask & first_return_mask_class_1

        # Apply combined mask to class 1 points

    # Comment out the DBSCAN part (no clustering applied)
    # coords_2d = np.vstack((reflectance_filtered_points.x, reflectance_filtered_points.y)).T
    # clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords_2d)
    # labels = clustering.labels_
    # unique_labels, counts = np.unique(labels, return_counts=True)
    # min_cluster_size = int(min_cluster_area * point_density)
    # large_cluster_labels = unique_labels[counts >= min_cluster_size]
    # vegetation_points = reflectance_filtered_points[np.isin(labels, large_cluster_labels)]



filter_tree_canopy(
    input_path= r'C:\Users\www\WRI-cif\Amsterdam\C_25GN1.LAZ',
    output_path= r'C:\Users\www\WRI-cif\Amsterdam\vegetation_test2.LAZ',
    bbx=(120764.46, 122764.46, 483845.95, 485845.95),  # Bounding box as (min_x, max_x, min_y, max_y)
    amplitude_threshold = 6.7,
    min_height=2.0,
    min_cluster_area=5,
    reflectance_threshold=0.3,
    eps=1.5,
    min_samples=5,
    point_density=1.5
)
#
#
# # Grid dimensions
# x_coords = np.arange(min_x, max_x, cell_size)
# y_coords = np.arange(min_y, max_y, cell_size)
# grid_width = len(x_coords)
# grid_height = len(y_coords)
#
# def generate_points_around(center_x, center_y, center_z, radius, num_points=10):
#     angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
#     return [(center_x + radius * np.cos(angle), center_y + radius * np.sin(angle), center_z) for angle in angles]
#
# # densifying the point cloud
# radius = 0.20
# densified_points = []
#
# for x, y, z in zip(filtered_points.x, filtered_points.y, filtered_points.z):
#     points_around = generate_points_around(x, y, z, radius)
#     densified_points.extend(points_around)
#
#
# heights = np.full((grid_height, grid_width), fill_value=np.nan, dtype=np.float64)
# for x, y, z in densified_points:
#     x_idx = int((x - min_x) / cell_size)
#     y_idx = int((max_y - y) / cell_size)
#     if 0 <= x_idx < grid_width and 0 <= y_idx < grid_height:
#         if np.isnan(heights[y_idx][x_idx]) or heights[y_idx, x_idx] < z:
#             heights[y_idx][x_idx] = z
#
#
# # Geospatial transform
# transform = from_origin(min_x, max_y, cell_size, cell_size)
#
# # Write to a TIFF file
# output_file_path = input("Enter the output file path for the vegetation raster: ")
#
# with rasterio.open(
#     output_file_path,  # Use the user-provided file path
#     'w',
#     driver='GTiff',
#     height=heights.shape[0],
#     width=heights.shape[1],
#     count=1,
#     dtype=heights.dtype,
#     crs='EPSG:7415',  # Setting the CRS to RDNAP
#     transform=transform
# ) as dst:
#     dst.write(heights, 1)
#
# print(f"vegetation raster saved to: {output_file_path}")




