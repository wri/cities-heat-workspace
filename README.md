# cities-heat-workspace - Amsterdam ctcm result comparison, local vs global data
In this branch of Amsterdam_comparison, the scripts are designed to do the preparation and preprocessing for the data and the analysis of the ctcm result. Instead having a complete workflow with a main function, the scripts have separated functions and are only used individually or in groups. 

## Data preparation
combine_dem_builidng.py takes two inputs - the DEM and building rasters, and output the result of putting building layer on top of the DEM. 
The building height layers tested with this script were rasterized vectors of buildings or rasterized point cloud from LiDAR data. The cells without building height are therefore wirtten as nodata. The DEM raster is first aligned and cropped to the building raster layer, filled with IDW interpolation in case there are empty cells. The building height values are finally put on top of the DEM layer. 

### Generating global data (vector to raster)
rasterize_gpkg.py is used on global building heght datasets which are usually gpkg files, to rasterize to the self-defined resolution and write the height of each building polygon to the rasterized cells. It also does cropping if you provide an aoi gpkg, which means the gpkg do not need to be preprocessed. 
To use it, it takes four parameters, input_gpkg is the file path to the building height, which should contain an attribute called height. aoi_gpkg is the file path for the aoi. The bounding box of the aoi defines the bbx of the output file. The output_tif is the path for the output tif file. Finally, the resolution can defined; by default, it is 1. 
### Generating local data (point cloud to raster)
dbscan_test.py was used to extract tree height from LiDAR data, in laz format. It is only used in Amsterdam, therefore, no guarantee if it will work for CRS other than EPSG:28992. To use it, the parameters for the dbscan can be tuned. It does clutering and noise removing in 2D, min_area_m2 is the minimum cluster area, by default 4; eps is the minimum distance between two clusters, by default 1, min_samples is the minimum number of points in one cluster, by default 50. 

laz_to_tif.py is used to write the height (z value) of a laz format point cloud file to a raster. It creates the cells of the self-defined resolution, then write the highest value of all the points in the cell to the tif file. To run it, it takes the input file path of the laz file, output path for the tif file, and resolution of the raster can be defined in resolution. 

## Preprocessing
### Aligning the input layers
The functions in check_raster_for_solweig.py align the input rasters and print out their information.

*The function align_rasters align the input raster layers' transform, crs, and shape. The first file from the input path will be used as reference for the aligning process, so it will not have an output (Use None for the first element in the output list). It takes a list of input raster file paths, and another list for the output raster file paths. 

*The function check_raster_layers print out the crs, resolution, origin, and shape of the input files, as well as the bounding box (bbx) of the rasters in EPSG:4326 to be put in the yml file of the ctcm setup. The parameter is a list of input file paths. 

## Analysis of the ctcm result - shadow
![image](https://github.com/user-attachments/assets/6531fde7-0893-483a-b6d9-e9d21ffc13d8)

### Statistics (non-spatial)
### Overlaying rasters for the difference map

## Analysis of the ctcm result - UTCI
### Generating UTCI rasters from TMRT result
### Overlaying UTCI results for difference
### Aggregating the UTCI difference based on resolution

## Result visualization
### Printing the maps
print_map.py can be used to create jnp format images from the raster layers taken as input. There are several legend styles, including shade, temp, tree_height, building_height, utci, utci_diff_reclass. Shade and utci_diff_reclass show discrete legend, while the other legend types are all continuous legend. To use the utci_diff_reclass, it is required to generate this reclassfied utci difference with the another script first (reclass_for_printing_map.py). 
To run this script, it takes four parameters. Input folder should contain the same structure mentioned earlier, so subfolders with run name including the tif files. It also requires an inset map that should be prepared in advance, in png format. The output path is a folder, and the output folder will have the same structure as the input file. Last but not least, do't forget to specify the legend style. 
reclass_for_printing_map.py reclassifies the UTCI raster to bins. The bins for now are hardcoded still. 
