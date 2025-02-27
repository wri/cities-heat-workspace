import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import Point, box
from rtree import index
import numpy as np
import pandas as pd

# Define the Stats class to store statistics
class Stats:
    def __init__(self, max_val, min_val, avg_val, stddev_val, num_points, avg_diff):
        self.max_val = max_val
        self.min_val = min_val
        self.avg_val = avg_val
        self.stddev_val = stddev_val
        self.num_points = num_points
        self.avg_diff = avg_diff  # Difference between average cell height and building height

    def __str__(self):
        return (f"Max: {self.max_val}, Min: {self.min_val}, Avg: {self.avg_val}, "
                f"Stddev: {self.stddev_val}, Points: {self.num_points}, Avg Diff: {self.avg_diff}")

# Function to calculate statistics for cell heights inside a polygon
def calculate_height_stats(cell_heights, building_height):
    avg_height = np.mean(cell_heights)
    stats = Stats(
        max_val=np.max(cell_heights),
        min_val=np.min(cell_heights),
        avg_val=avg_height,
        stddev_val=np.std(cell_heights),
        num_points=len(cell_heights),
        avg_diff=avg_height - building_height  # Difference between avg height of cells and building height
    )
    return stats

def generate_cell_centers_and_heights(cropped_data, transform):
    # Check if the raster data is multi-band and select the first band
    if cropped_data.ndim == 3:
        data = cropped_data[0]  # Use the first band
    else:
        data = cropped_data  # It's already a single-band data

    raster_height, raster_width = data.shape
    cell_centers_and_heights = []

    # Loop over the rows and columns of the raster to get the center points and heights
    for row in range(raster_height):
        for col in range(raster_width):
            x, y = rasterio.transform.xy(transform, row, col, offset='center')
            height = data[row, col]  # Get the height value from the raster
            cell_centers_and_heights.append((Point(x, y), height))  # Store center point and height

    return cell_centers_and_heights

# Function to build an R-tree spatial index for fast lookups
def build_spatial_index(cell_centers_and_heights):
    idx = index.Index()
    for i, (point, height) in enumerate(cell_centers_and_heights):
        idx.insert(i, (point.x, point.y, point.x, point.y))  # Insert point's bounding box into the index
    return idx

# Function to find points inside a polygon using R-tree spatial index
def points_in_polygon(polygon, cell_centers_and_heights, spatial_idx):
    candidates = list(spatial_idx.intersection(polygon.bounds))  # Get candidate points by bounding box
    points_within_polygon = [(cell_centers_and_heights[i][0], cell_centers_and_heights[i][1]) for i in candidates if polygon.contains(cell_centers_and_heights[i][0])]  # Exact check
    return points_within_polygon

# Function to process each building and calculate statistics for points inside the polygon
def process_buildings(cropped_raster_data, cropped_vector_data, transform, nodata_value=None, output_csv_path='building_stats.csv', updated_vector_path = 'building_height_updated.gpkg'):
    # Generate cell centers and heights from the cropped raster
    cell_centers_and_heights = generate_cell_centers_and_heights(cropped_raster_data, transform)

    # Build the spatial index for all cell centers
    spatial_idx = build_spatial_index(cell_centers_and_heights)

    # Store building stats in a dictionary
    building_stats = {}

    # Lists to store differences for overall performance
    all_diffs = []
    height_diffs = []


    # Find the correct height column
    height_column_names = ['height', 'Height', 'heights', 'Heights', 'building heights', 'Building heights',
                           'building_height', 'Building_height', 'building_heights', 'Building_heights']
    found_column = None
    for column_name in height_column_names:
        if column_name in cropped_vector_data.columns:
            found_column = column_name
            break

    if found_column is None:
        raise KeyError("No column representing building height found in the data.")

    csv_data = []

    # Loop through each building polygon in the vector file
    for idx, building in cropped_vector_data.iterrows():
        building_polygon = building.geometry
        building_height = building[found_column]  # Use the found column

        # Find the cell centers inside the building polygon
        points_in_poly = points_in_polygon(building_polygon, cell_centers_and_heights, spatial_idx)

        # Collect heights for the points within the polygon, filtering out nodata and extremely large values
        cell_heights = [height for point, height in points_in_poly
                        if (nodata_value is None or height != nodata_value) and height < 1e6]

        # Calculate stats if there are any valid points in the polygon
        if cell_heights:
            stats = calculate_height_stats(cell_heights, building_height)
            # Use 'id' if available, otherwise use the index as a unique key
            building_id = building['id'] if 'id' in building else idx
            building_stats[building_id] = stats

            # Append the difference to the overall performance list
            all_diffs.append(stats.avg_diff)
            csv_data.append(
                [building_id, stats.max_val, stats.min_val, stats.avg_val, stats.stddev_val, stats.num_points,
                 stats.avg_diff])
            height_diffs.append(stats.avg_diff)
        else:
            # If no points are found, use NaN or zero for differences
            height_diffs.append(np.nan)
            csv_data.append([building_id, np.nan, np.nan, np.nan, np.nan, 0, np.nan])

    # Calculate overall performance
    avg_diff = np.mean(all_diffs) if all_diffs else 0
    stddev_diff = np.std(all_diffs) if all_diffs else 0

    df = pd.DataFrame(csv_data,
                      columns=['Building ID', 'Max Height', 'Min Height', 'Avg Height', 'Stddev Height', 'Num Points',
                               'Avg Height Diff'])
    df.to_csv(output_csv_path, index=False)

    cropped_vector_data['height_difference'] = height_diffs

    cropped_vector_data.to_file(updated_vector_path, driver='GPKG')

    return building_stats, avg_diff, stddev_diff, cropped_vector_data
