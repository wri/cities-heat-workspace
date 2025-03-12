# cities-heat-workspace - Amsterdam ctcm result comparison, local vs global data
In this branch of Amsterdam_comparison, the scripts are designed to do the preparation and preprocessing for the data and the analysis of the ctcm result. Instead having a complete workflow with a main function, the scripts have separated functions and are only used individually or in groups. 

## Data preparation
### Generating global data

### Generating local data

## Preprocessing
### Aligning the input layers
The functions in check_raster_for_solweig.py align the input rasters and print out their information. 
*The function align_rasters align the input raster layers' transform, crs, and shape. It takes a list of input raster file paths, and another list for the output raster file paths. 

## Analysis of the ctcm result - shadow
### Statistics (non-spatial)
### Overlaying rasters for the difference map

## Analysis of the ctcm result - UTCI
### Generating UTCI rasters from TMRT result
### Overlaying UTCI results for difference
### Aggregating the UTCI difference based on resolution

## Result visualization
### Printing the maps
