# cities-heat-workspace - Amsterdam ctcm result comparison, local vs global data
In this branch of Amsterdam_comparison, the scripts are designed to do the preparation and preprocessing for the data and the analysis of the ctcm result. Instead having a complete workflow with a main function, the scripts have separated functions and are only used individually or in groups. 

## Data preparation
### Generating global data

### Generating local data

## Preprocessing
### Aligning the input layers
The functions in check_raster_for_solweig.py align the input rasters and print out their information.

*The function align_rasters align the input raster layers' transform, crs, and shape. The first file from the input path will be used as reference for the aligning process, so it will not have an output (Use None for the first element in the output list). It takes a list of input raster file paths, and another list for the output raster file paths. 

*The function check_raster_layers print out the crs, resolution, origin, and shape of the input files, as well as the bounding box (bbx) of the rasters in EPSG:4326 to be put in the yml file of the ctcm setup. The parameter is a list of input file paths. 

## Analysis of the ctcm result - shadow
### Statistics (non-spatial)
### Overlaying rasters for the difference map

## Analysis of the ctcm result - UTCI
### Generating UTCI rasters from TMRT result
### Overlaying UTCI results for difference
### Aggregating the UTCI difference based on resolution

## Result visualization
### Printing the maps
