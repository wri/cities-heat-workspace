import numpy as np
import laspy
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull
import scipy
from shapely.geometry import MultiPoint


def filter_points(input_laz_path, output_laz_path, min_area_m2=4, eps=1, min_samples=50, aspect_ratio_threshold=7 ):
    """
    Filters points to retain clusters that are likely trees based on area criteria.

    Parameters:
    - input_laz_path: path to the LAS/LAZ file.
    - min_area_m2: minimum area in square meters for a cluster to be retained.
    - eps: the maximum distance between two samples for one to be considered as in the neighborhood of the other.
    - min_samples: the number of samples in a neighborhood for a point to be considered as a core point.
    """
    with laspy.open(input_laz_path) as infile:
        las = infile.read()

    # Extract coordinates
    coords = np.vstack((las.x, las.y)).T

    # Perform DBSCAN clustering
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    labels = db.labels_

    # Collect indices for valid clusters
    valid_indices = []

    # Analyze each cluster
    for k in set(labels):
        if k == -1:  # Ignore noise
            continue

        # Extract points belonging to the current cluster
        cluster_mask = (labels == k)
        cluster_points = coords[cluster_mask]

        if len(cluster_points) < 3:
            continue  # Not enough points to form a convex hull

        try:
            # Calculate the convex hull and then the minimum bounding rectangle
            hull = ConvexHull(cluster_points)
            if hull.volume > min_area_m2:  # Check the convex hull area
                multipoint = MultiPoint(cluster_points)
                min_rectangle = multipoint.minimum_rotated_rectangle

                # Calculate the aspect ratio of the minimum bounding rectangle
                x, y = min_rectangle.exterior.coords.xy
                edge_length = [np.linalg.norm(np.array([x[i], y[i]]) - np.array([x[i + 1], y[i + 1]])) for i in range(len(x) - 1)]
                length, width = max(edge_length), min(edge_length)
                aspect_ratio = length / width

                if aspect_ratio <= aspect_ratio_threshold:
                    valid_indices.extend(np.where(cluster_mask)[0])

        except scipy.spatial.qhull.QhullError:
            continue  # Skip clusters that cannot form a valid convex hull

    # Ensure indices are unique before writing
    valid_indices = list(set(valid_indices))  # Remove any duplicates

    # Filtered points ready for writing
    if valid_indices:
        vegetation_points = las.points[valid_indices]
        with laspy.open(output_laz_path, mode='w', header=las.header) as writer:
            writer.write_points(vegetation_points)

    print(f"Filtered {len(valid_indices)} points into {output_laz_path}")


# Use the function
output_path= r'C:\Users\www\WRI-cif\Amsterdam\dbscan_test.LAZ'
#filtered_points = filter_points(r'C:\Users\www\WRI-cif\Amsterdam\vegetation_test2.LAZ', r'C:\Users\www\WRI-cif\Amsterdam\dbscan_test.LAZ', min_area_m2=4, eps=1, min_samples=50)
filtered_points = filter_points(r'C:\Users\www\WRI-cif\Amsterdam\dbscan_test1.LAZ', r'C:\Users\www\WRI-cif\Amsterdam\dbscan_test2.LAZ', min_area_m2=4, eps=1, min_samples=50, aspect_ratio_threshold=7)
# print(f"Filtered points count: {len(filtered_points)}")

