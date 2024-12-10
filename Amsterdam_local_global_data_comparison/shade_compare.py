import rasterio
import numpy as np
from rasterio.windows import Window, from_bounds
import pandas as pd
import os


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

