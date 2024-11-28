import numpy as np
from osgeo import gdal


def read_raster(raster_path):
    """
    Reads a raster file and returns the array, NoData value, and geo-transform.
    """
    ds = gdal.Open(raster_path)
    band = ds.GetRasterBand(1)
    array = band.ReadAsArray()
    nodata = band.GetNoDataValue()
    transform = ds.GetGeoTransform()
    return array, nodata, transform


def bilinear_interpolation(input_array, nodata_value):
    """
    Performs bilinear interpolation to fill NoData values.

    Args:
    - input_array: The 2D array representing the raster.
    - nodata_value: The value representing NoData in the array.

    Returns:
    - Interpolated array with NoData values filled.
    """
    filled_array = input_array.copy()
    rows, cols = input_array.shape

    for y in range(1, rows - 1):
        for x in range(1, cols - 1):
            if filled_array[y, x] == nodata_value:
                # Get values of the four neighboring cells
                neighbors = [
                    input_array[y - 1, x],  # Top
                    input_array[y + 1, x],  # Bottom
                    input_array[y, x - 1],  # Left
                    input_array[y, x + 1]  # Right
                ]

                # Filter out NoData values
                valid_neighbors = [val for val in neighbors if val != nodata_value]

                # If there are valid neighbors, compute the average
                if valid_neighbors:
                    filled_array[y, x] = np.mean(valid_neighbors)

    return filled_array


def write_raster(output_path, array, transform, nodata_value, reference_path):
    """
    Writes the interpolated array to a new raster file.
    """
    ref_ds = gdal.Open(reference_path)
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_path, array.shape[1], array.shape[0], 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(transform)
    out_ds.SetProjection(ref_ds.GetProjection())

    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(array)
    out_band.SetNoDataValue(nodata_value)

    out_band.FlushCache()
    out_ds.FlushCache()


def main(dtm_path, dsm_path, dtm_output, dsm_output):
    # Read the DTM and DSM rasters
    dtm_array, dtm_nodata, transform = read_raster(dtm_path)
    dsm_array, dsm_nodata, _ = read_raster(dsm_path)

    # Interpolate NoData values in DTM and DSM using bilinear interpolation
    dtm_filled = bilinear_interpolation(dtm_array, dtm_nodata)
    dsm_filled = bilinear_interpolation(dsm_array, dsm_nodata)

    # Write the filled arrays to new raster files
    write_raster(dtm_output, dtm_filled, transform, dtm_nodata, dtm_path)
    write_raster(dsm_output, dsm_filled, transform, dsm_nodata, dsm_path)

    print(f"Filled DTM saved to: {dtm_output}")
    print(f"Filled DSM saved to: {dsm_output}")


if __name__ == "__main__":
    # Paths to input and output files
    dtm_path = "path/to/your/dtm.tif"
    dsm_path = "path/to/your/dsm.tif"
    dtm_output = "path/to/your/filled_dtm.tif"
    dsm_output = "path/to/your/filled_dsm.tif"

    # Run the main function
    main(dtm_path, dsm_path, dtm_output, dsm_output)
