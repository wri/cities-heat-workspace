import laspy
import numpy as np


def merge_laz_files(input_file1, input_file2, output_file):
    """
    Merge two LAZ files into one, keeping only X, Y, Z coordinates.

    Parameters:
        input_file1 (str): Path to the first LAZ file.
        input_file2 (str): Path to the second LAZ file.
        output_file (str): Path for the output merged LAZ file.
    """
    # Read the first LAZ file
    with laspy.open(input_file1) as las1:
        points1 = las1.read()

    # Read the second LAZ file
    with laspy.open(input_file2) as las2:
        points2 = las2.read()

    # Extract only X, Y, Z (ignore extra attributes)
    xyz1 = np.vstack((points1.x, points1.y, points1.z)).T
    xyz2 = np.vstack((points2.x, points2.y, points2.z)).T

    # Merge the X, Y, Z points
    merged_xyz = np.vstack((xyz1, xyz2))

    # Create a new LAS header based on the first file's header
    merged_header = laspy.LasHeader(point_format=points1.header.point_format, version=points1.header.version)

    # Pass all scales and offsets from the first file
    merged_header.scales = points1.header.scales
    merged_header.offsets = points1.header.offsets

    # Create new point record with correct scales and offsets
    merged_points = laspy.ScaleAwarePointRecord.zeros(
        len(merged_xyz),  # Correctly passing the number of points
        point_format=merged_header.point_format,
        scales=merged_header.scales,
        offsets=merged_header.offsets
    )

    # Assign X, Y, Z values
    merged_points.x = merged_xyz[:, 0]
    merged_points.y = merged_xyz[:, 1]
    merged_points.z = merged_xyz[:, 2]

    # Write the merged points to the output file
    with laspy.open(output_file, mode="w", header=merged_header) as las_out:
        las_out.write_points(merged_points)

    print(f"Merging completed: {output_file}")


merge_laz_files(r'C:\Users\www\WRI-cif\Amsterdam\Laz_result\aoi2\aoi2_2.LAZ',
                r'C:\Users\www\WRI-cif\Amsterdam\Laz_result\aoi2\aoi2_1.LAZ',
                r'C:\Users\www\WRI-cif\Amsterdam\Laz_result\aoi2\aoi2_tree_m.LAZ')
