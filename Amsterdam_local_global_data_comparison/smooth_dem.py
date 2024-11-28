import rasterio
from rasterio.enums import Resampling
import numpy as np
from scipy.ndimage import gaussian_filter


def smooth_dem(input_path, output_path, sigma=1):
    """
    Smooth a DEM from 30m to 1m resolution using interpolation and Gaussian smoothing.

    Parameters:
    - input_path: str, path to the input DEM file.
    - output_path: str, path to save the smoothed DEM.
    - sigma: float, standard deviation for Gaussian filter (controls smoothing).
    """
    # Open the input DEM
    with rasterio.open(input_path) as src:
        dem_data = src.read(1)  # Read the first band
        transform = src.transform
        profile = src.profile

        # Calculate the target resolution
        new_resolution = 1  # Target resolution in meters
        scale_factor = src.res[0] / new_resolution

        # Upscale the DEM using bilinear interpolation
        new_height = int(dem_data.shape[0] * scale_factor)
        new_width = int(dem_data.shape[1] * scale_factor)
        upscaled_dem = src.read(
            out_shape=(1, new_height, new_width),
            resampling=Resampling.bilinear
        )[0]

        # Smooth the upscaled DEM using a Gaussian filter
        smoothed_dem = gaussian_filter(upscaled_dem, sigma=sigma)

        # Update the metadata for the output file
        profile.update(
            height=new_height,
            width=new_width,
            transform=transform * transform.scale(
                1 / scale_factor, 1 / scale_factor
            )
        )

        # Write the smoothed DEM to the output file
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(smoothed_dem, 1)

    print(f"Smoothed DEM saved to {output_path}")
    return output_path


smooth_dem(input_dem_path, output_dem_path, sigma=5)