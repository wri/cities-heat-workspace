import rasterio
import numpy as np
from rasterio.windows import Window

def read_raster(file_path):
    """Read a raster file and return the data and metadata."""
    with rasterio.open(file_path) as src:
        data = src.read(1)  # Read the first band
    return data

def calculate_total_shadow_area(shade_map):
    """Calculate the total area of shadow (value 0) in square meters."""
    shadow_pixels = np.sum(shade_map == 0)  # Count pixels with value 0
    total_area = shadow_pixels  # Each pixel represents 1 m², so the total area is the count
    return total_area


def cut_raster_edges(raster_path, output_path, buffer=400):
    """
    Cut a buffer (in meters) from each edge of a raster and save the result.

    Parameters:
        raster_path (str): Path to the input raster file.
        output_path (str): Path to save the cropped raster.
        buffer (int): Buffer distance in meters to remove from each edge.

    Returns:
        numpy.ndarray: The cropped raster data.
    """
    with rasterio.open(raster_path) as src:
        # Calculate pixel buffer based on raster resolution
        buffer_pixels = int(buffer / src.res[0])  # Assuming square pixels

        # Create a window to cut the buffer
        height, width = src.height, src.width
        window = Window(buffer_pixels, buffer_pixels,
                        width - 2 * buffer_pixels,
                        height - 2 * buffer_pixels)

        # Read the data within the window
        data = src.read(1, window=window)

        # Update the transform to reflect the window
        transform = src.window_transform(window)

        # Save the cropped raster
        profile = src.profile
        profile.update({
            "height": data.shape[0],
            "width": data.shape[1],
            "transform": transform
        })
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data, 1)

    return data

def calculate_difference(map1, map2):
    """Calculate the difference between two shade maps."""
    return map2 - map1

def calculate_overlap_area(map1, map2):
    """Calculate the overlap of shadow areas between two maps."""
    overlap = np.sum((map1 == 0) & (map2 == 0))  # Both maps have shadow (value 0) in the same pixel
    return overlap

def calculate_newly_shaded_area(map1, map2):
    """Calculate the newly shaded area in map2 compared to map1."""
    newly_shaded = (map1 == 1) & (map2 == 0)  # Pixels not shadowed in map1 but shadowed in map2
    newly_shaded_area = np.sum(newly_shaded)
    return newly_shaded_area

def calculate_lost_shaded_area(map1, map2):
    """Calculate the lost shadow area from map1 to map2."""
    lost_shaded = (map1 == 0) & (map2 == 1)  # Pixels shadowed in map1 but not shadowed in map2
    lost_shaded_area = np.sum(lost_shaded)
    return lost_shaded_area

def generate_statistics(diff_map):
    """Generate statistics for the difference map."""
    stats = {
        "min_difference": np.min(diff_map),
        "max_difference": np.max(diff_map),
        "mean_difference": np.mean(diff_map),
        "std_difference": np.std(diff_map),
    }
    return stats

def analyze_shade_maps(file1, file2):
    """Analyze two shade maps and return key metrics."""
    map1 = read_raster(file1)
    map2 = read_raster(file2)

    total_area_map1 = calculate_total_shadow_area(map1)
    total_area_map2 = calculate_total_shadow_area(map2)
    diff_map = calculate_difference(map1, map2)
    overlap_area = calculate_overlap_area(map1, map2)
    newly_shaded_area = calculate_newly_shaded_area(map1, map2)
    lost_shaded_area = calculate_lost_shaded_area(map1, map2)
    stats = generate_statistics(diff_map)

    return {
        "total_shadow_area_map1": total_area_map1,
        "total_shadow_area_map2": total_area_map2,
        "overlap_area": overlap_area,
        "newly_shaded_area": newly_shaded_area,
        "lost_shaded_area": lost_shaded_area,
        "statistics": stats,
    }

# Example Usage
file1 = "path_to_shade_map1.tif"
file2 = "path_to_shade_map2.tif"

results = analyze_shade_maps(file1, file2)
print("Shade Map Analysis Results:", results)
