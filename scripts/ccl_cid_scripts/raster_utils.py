import os
import json
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles
import rioxarray
from rasterio.enums import Resampling
from typing import List, Tuple, Union
import rasterio
from rasterio.warp import reproject, Resampling
import numpy
import numpy.ma as ma
from network_utils import download_file_from_url
from s3_utils import upload_file_to_s3_bucket
from vector_utils import reproject_geojson


def convert_to_cog_and_validate(
    src_path: str, dst_path: str, profile="deflate"
) -> Union[str, None]:
    """
    Convert the file located as src_path into a COG.
    ### Args:
        src_path - path+filename of the source file
        dst_path - path+filename of where the COG should be generated and stored
        profile - the profile by which the COG should be generated (Refer to https://cogeotiff.github.io/rio-cogeo/profile/)
    ### Returns:
        Error message if failed or None if success
    """
    try:
        output_profile = cog_profiles.get(profile)
        raster = rasterio.open(src_path)
        profile = raster.profile
        if profile["dtype"] in ["uint8", "uint16", "uint32"]:
            output_profile["dtype"] = numpy.int32
        output_profile["crs"] = "EPSG:4326"
        output_profile.update(dict(BIGTIFF="IF_SAFER"))

        # Dataset Open option (see gdalwarp `-oo` option)
        config = dict(
            GDAL_NUM_THREADS="ALL_CPUS",
            GDAL_TIFF_INTERNAL_MASK=True,
            GDAL_TIFF_OVR_BLOCKSIZE="128",
        )

        cog_translate(
            src_path,
            dst_path,
            output_profile,
            nodata=-999,
            config=config,
            in_memory=False,
            use_cog_driver=True,
            quiet=True,
        )
        print("Validating COG..")
        cog_validity = cog_validate(dst_path)
        # print(cog_validity)
        if not cog_validity[0]:
            raise Exception("Error validating generated COG.")
    except Exception as e:
        return f"Error converting file {src_path} to COG: {str(e)}"
    else:
        return None


def check_and_reproject(
    file_path: str, projection: str = "EPSG:4326"
) -> Union[List[str], None]:
    """
    Give the file location for a geotiff file, check its projection
    and if it is not the same as the projection parameter, then
    reproject it to the given projection and save it in place

    ### Args:
        - file_path - path to a geotiff file that needs to be reprojected

    """

    try:
        xds = rioxarray.open_rasterio(file_path, decode_coords="all")
        if not xds.rio.crs:
            print("No CRS found so writing CRS.")
            xds.rio.write_crs(projection, inplace=True)
            xds.rio.to_raster(file_path)
        elif xds.rio.crs != projection:
            # Need to reproject
            print(f"Reprojecting Geotiff file to {projection}")
            xds1 = xds.rio.reproject(projection)
            xds1.rio.to_raster(file_path)
        else:
            # Already in the required projection so do nothing
            pass
    except Exception as e:
        return f"Error reprojection file {file_path}: {str(e)}"
    else:
        return None


def check_between_bounds(arr: list, lower_bound, upper_bound, inclusive: bool) -> bool:
    """Check if elements in an array are between the specified bounds"""
    try:
        for element in arr:
            if inclusive:
                if element < lower_bound or element > upper_bound:
                    return None, False
            else:
                if element <= lower_bound or element >= upper_bound:
                    return None, False
        return None, True
    except Exception as e:
        return f"Error checking if array values between bounds: {str(e)}", False


def get_unique_pixel_values(file_path: str) -> Union[set, None]:
    """Return a set of the unique pixel values in a given TIF file"""
    pixel_values = None
    try:
        raster = rasterio.open(file_path)
        band_array = raster.read(1)
        pixel_values = []
        for x in range(band_array.shape[0]):
            for y in range(band_array.shape[1]):
                pixel_values.append(band_array[x, y].item())
    except Exception as e:
        return None, f"Error getting pixel values in raster: {str(e)}"
    else:
        return set(pixel_values), None


def replace_pixel_values_between_exclusive(
    file_path: str, gt_value, lt_value, value_to_replace
) -> Union[str, None]:
    """Replace all pixel values which are between the specified bounds with the provided value"""
    try:
        raster = rasterio.open(file_path)
        profile = raster.profile
        band_array = raster.read(1)
        if not value_to_replace:
            value_to_replace = -999
        band_array[(band_array > gt_value) & (band_array < lt_value)] = value_to_replace
        profile["nodata"] = -999
        with rasterio.open(file_path, "w", **(profile)) as dst:
            dst.write(band_array, 1)

    except Exception as e:
        return f"Error replacing pixel values between exclusive in raster: {str(e)}"
    else:
        return None


def replace_nans_in_raster_with(
    file_path: str, value_to_replace=-999
) -> Union[str, None]:
    """Replace numpy NaNs in the raster with the provided value"""
    try:
        raster = rasterio.open(file_path)
        # print(raster.nodatavals)
        profile = raster.profile
        if profile["dtype"] in ["uint8", "uint16", "uint32"]:
            profile["dtype"] = numpy.int32
        band_array = raster.read(1)
        band_array = numpy.nan_to_num(band_array, nan=value_to_replace)
        profile["nodata"] = -999
        # print("writing")
        with rasterio.open(file_path, "w", **(profile)) as dst:
            dst.write(band_array, 1)
    except Exception as e:
        return f"Error replacing nans in raster: {str(e)}"
    else:
        return None


def replace_pixel_values_with_condition(
    file_path: str, condition_value, value_to_replace, condition: str
) -> Union[str, None]:
    """Replace pixels values that match the specified condition with the provided value"""
    try:
        raster = rasterio.open(file_path)
        # print(raster.nodatavals)
        profile = raster.profile
        if profile["dtype"] in ["uint8", "uint16", "uint32"]:
            profile["dtype"] = numpy.int32
        band_array = raster.read(1)
        if not value_to_replace:
            value_to_replace = -999
        if condition == ">":
            band_array[band_array > condition_value] = value_to_replace
        elif condition == ">=":
            band_array[band_array >= condition_value] = value_to_replace
        elif condition == "<":
            band_array[band_array < condition_value] = value_to_replace
        elif condition == "<=":
            band_array[band_array <= condition_value] = value_to_replace
        elif condition == "==":
            band_array[band_array == condition_value] = value_to_replace
        elif condition == "!=":
            band_array[band_array != condition_value] = value_to_replace
        profile["nodata"] = -999
        # print("writing")
        with rasterio.open(file_path, "w", **(profile)) as dst:
            dst.write(band_array, 1)

    except Exception as e:
        return f"Error replacing pixel values {condition} than in raster: {str(e)}"
    else:
        return None


def logical_not_pixel_values(file_path: str) -> Union[str, None]:
    """Switch all 1's to 0 and 0's to 1"""
    try:
        raster = rasterio.open(file_path)
        # print(raster.nodatavals)
        profile = raster.profile
        if profile["dtype"] in ["uint8", "uint16", "uint32"]:
            profile["dtype"] = numpy.int32
        band_array = raster.read(1)

        zero_array = numpy.where(band_array == 0)
        one_array = numpy.where(band_array == 1)
        band_array[zero_array] = 1
        band_array[one_array] = 0

        profile["nodata"] = -999
        # print("writing")
        with rasterio.open(file_path, "w", **(profile)) as dst:
            dst.write(band_array, 1)

    except Exception as e:
        return f"Error performing logical not of pixel values in raster: {str(e)}"
    else:
        return None


def convert_pixel_values_to_int(file_path: str) -> Union[str, None]:
    """Convert all pixel values to closest integer values"""
    try:
        raster = rasterio.open(file_path)
        profile = raster.profile
        # print(profile)
        profile["dtype"] = numpy.int32
        band_array = raster.read(1)
        profile["nodata"] = -999
        with rasterio.open(file_path, "w", **(profile)) as dst:
            dst.write(band_array, 1)
    except Exception as e:
        return f"Error converting pixel values to int in raster: {str(e)}"
    else:
        return None


def generate_masked_tif_using_geojson(
    mask_file, src_file, dest_file_name
) -> Union[str, None]:
    """Given a geojson mask file, mask the provided tif file with it"""
    try:
        # Make sure both the mask and sources have the same projection
        reproject_geojson(mask_file)
        check_and_reproject(src_file)

        with open(mask_file, "r") as f:
            gj = json.load(f)
            shapes = [feature["geometry"] for feature in gj["features"]]
            crs = "EPSG:4326"
            # create mask raster based on the input raster
            rds = rioxarray.open_rasterio(src_file).isel(band=0)
            if rds.dtype in ["uint8", "uint16", "uint32"]:
                rds = rds.astype(numpy.int32)
            rds.rio.write_nodata(-999, inplace=True)
            # clip the raster to the mask
            clipped = rds.rio.clip(shapes, crs, drop=False)

            # write output to file
            clipped.rio.to_raster(dest_file_name, nodata=-999)
    except Exception as e:
        return f"Error clipping to geojson: {str(e)}"
    else:
        return None


def generate_masked_tif_using_tif(mask_file, src_file, dest_file_name):
    """Given a tif mask file, mask the provided tif wiith it"""
    try:
        error = check_and_reproject(mask_file)
        if error:
            raise Exception(error)
        error = check_and_reproject(src_file)
        if error:
            raise Exception(error)

        mask_raster = rasterio.open(mask_file)
        mask_band_array = mask_raster.read(1)

        input_raster = rasterio.open(src_file)
        input_band_array = input_raster.read(1)

        profile = input_raster.profile
        profile["nodata"] = -999
        if profile["dtype"] in ["uint8", "uint16", "uint32"]:
            profile["dtype"] = numpy.int32

        masked_array = ma.array(
            input_band_array, mask=numpy.logical_not(mask_band_array)
        )
        if masked_array.dtype in ["uint8", "uint16", "uint32"]:
            masked_array = masked_array.astype(numpy.int32)
        masked_filled_array = ma.filled(masked_array, fill_value=-999)
        # print(
        #    "masked array", numpy.min(masked_filled_array), numpy.max(masked_filled_array)
        # )
        with rasterio.open(
            dest_file_name,
            "w",
            **profile,
        ) as dst:
            dst.write(masked_filled_array, 1)
    except Exception as e:
        return str(e)


def generate_diff_raster(
    orig_file_location_with_name: str,
    to_be_subtracted_file_location_with_name: str,
    destination_file_location_with_name: str,
) -> Union[str, None]:
    """
    Given a location of an original file and the location of a file
    whose values need to be deducted from the original, this
    function generates a TIF with the difference in pixel
    values between the two
    """

    try:
        orig_src = rioxarray.open_rasterio(
            orig_file_location_with_name, decode_coords="all"
        )
        orig_crs = orig_src.rio.crs
        # print("Orig file crs is ", orig_crs)

        tbs_src = rioxarray.open_rasterio(
            to_be_subtracted_file_location_with_name, decode_coords="all"
        )
        tbs_crs = tbs_src.rio.crs
        # print("To be subtracted crs is ", tbs_src.rio.crs)

        if orig_crs != tbs_crs:
            raise Exception("CRSs of the source files are not the same.")

        tbs_raster = rasterio.open(to_be_subtracted_file_location_with_name)
        tbs_band_array = tbs_raster.read(1)

        orig_raster = rasterio.open(orig_file_location_with_name)
        orig_band_array = orig_raster.read(1)

        profile = orig_raster.profile

        diff_array = numpy.subtract(orig_band_array, tbs_band_array)
        profile["nodata"] = -999
        with rasterio.open(
            destination_file_location_with_name, "w", **(profile)
        ) as dst:
            dst.write(diff_array, 1)
    except Exception as e:
        return f"Error calculating difference between vectors: {str(e)}"
    else:
        return None


def match_raster_shape(
    source_file: str,
    target_file: str,
    output_file: str,
    resampling_method=Resampling.nearest,
) -> Union[str, None]:
    """
    Reshape a source raster to match the shape (extent, resolution, CRS) of a target raster.

    Parameters:
    - source_file: Path to the raster file to be reshaped
    - target_file: Path to the raster file whose shape should be matched
    - output_file: Path where the output raster will be saved
    - resampling_method: Resampling method from rasterio.warp.Resampling (default: nearest)

    Returns:
    - None (writes output to file)
    """
    try:
        # Open the source and target rasters
        with rasterio.open(source_file) as src:
            source_data = src.read()
            source_profile = src.profile.copy()

            with rasterio.open(target_file) as target:
                # Check if we need to do anything at all first
                if src.height == target.height and src.width == target.width:
                    # Nothing to do so return
                    return None

                # Update the output profile with target's shape and transform
                output_profile = source_profile.copy()
                output_profile.update(
                    {
                        "height": target.height,
                        "width": target.width,
                        "transform": target.transform,
                        "crs": target.crs,
                    }
                )

                # Create output array
                output_data = numpy.zeros(
                    (src.count, target.height, target.width), dtype=source_data.dtype
                )

                # Perform the reprojection
                reproject(
                    source_data,
                    output_data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=target.transform,
                    dst_crs=target.crs,
                    resampling=resampling_method,
                )
                # Write the output file
                with rasterio.open(output_file, "w", **output_profile) as dst:
                    dst.write(output_data)
    except Exception as e:
        return ("Error matching raster shapes: ", str(e))
    else:
        return None


def download_convert_upload(
    source_url: str,
    destination_bucket: str,
    destination_path: str,
    destination_filename: str,
    data_dir: str,
) -> Union[str, None]:
    """Used to download a tif, reproject, convert to COG and upload. Needs tweaking"""
    try:
        DATA_DIR = data_dir
        # print(tif_url)

        local_tif_path_with_filename = os.path.join(DATA_DIR, destination_filename)
        file_name_without_extension, extension = os.path.splitext(destination_filename)
        local_cog_path_with_filename = (
            os.path.join(DATA_DIR, file_name_without_extension) + "_cog.tif"
        )
        s3_tif_path_with_filename = os.path.join(
            destination_path, "tif", destination_filename
        )
        s3_cog_path_with_filename = os.path.join(
            destination_path, "cog", destination_filename
        )
        print(
            local_cog_path_with_filename,
            local_tif_path_with_filename,
            s3_tif_path_with_filename,
            s3_cog_path_with_filename,
        )
        print(f"Downloading {source_url} to {local_tif_path_with_filename}")
        error = download_file_from_url(source_url, local_tif_path_with_filename)
        if error:
            raise Exception(error)
        check_and_reproject(local_tif_path_with_filename)

        print("Converting to COG")
        error = convert_to_cog_and_validate(
            local_tif_path_with_filename,
            local_cog_path_with_filename,
        )
        if error:
            raise Exception(error)
        print("Uploading TIF to S3..")
        error = upload_file_to_s3_bucket(
            local_tif_path_with_filename,
            destination_bucket,
            s3_tif_path_with_filename,
        )
        if error:
            raise Exception(error)
        print("Uploading COG to S3..")
        error = upload_file_to_s3_bucket(
            local_cog_path_with_filename,
            destination_bucket,
            s3_cog_path_with_filename,
        )
        if error:
            raise Exception(error)
    except Exception as e:
        err = f"Error processing layer UrbanLandUse__uluclass_informal: {str(e)}"
        print(err)
        return err
    else:
        return None


def generate_raster_layer_filename(
    city_id: str, aoi_id, layer_id: str, year: str
) -> Tuple[str, Union[str, None]]:
    """
    Given the input parameters generate and return the layer
    filename in the correct format or None and an error message
    in case of errors. Parameters are self explanatory.
    """
    if None in [city_id, aoi_id, layer_id, year]:
        return None, "City ID, AOI ID, layer ID and year should all be specified"
    else:
        return f"{city_id}__{aoi_id}__{layer_id}__{year}", None
