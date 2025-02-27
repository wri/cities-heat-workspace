# cities-heat-workspace - building height comparison
A brief description of what this project does and who it's for.

## Description of the method
The Raster Cell Center Approach compares building heights by calculating the center of each raster cell and verifying whether it falls within a building footprint polygon. Only raster cells whose centers are located within the polygons contribute to the height calculations, ensuring precision and relevance in the derived measurements.

### Analysis Workflow
Check Cell Center Within Polygon: Evaluate whether the center of each raster cell is within a building footprint polygon.
Height List Compilation: For cells within a polygon, compile a list of raster heights.
Average Height Calculation: Calculate the average height from the compiled list for each building.
Comparison: Compare the average raster-derived height to the building height noted in the vector data.

### Advantages:
Avoids biases typical of rasterization by focusing solely on cell centers within building footprints.
Adaptable to buildings of varying sizes, shapes, and footprints, providing flexibility across diverse urban settings.
Do not need manual preprocessing of the input layers

## Data Requirements
### The input data should include three parts:

An area of interest (recommended size is 2km by 2km to avoid long processing time). The file can be in any format that can be read by geopandas (like geojson or geopackage). The CRS of this file will determine the CRS in the calculation process and in the result. 

A vector building height dataset that contains the attribute for building height, named in any of the following: 

'height', 'Height', 'heights', 'Heights', 'building heights', 'Building heights',
'building_height', 'Building_height', 'building_heights', 'Building_heights'

A DSM raster layer, which can be in any resolution or CRS. Both the building height vector layer and the DSM raster should be at least the same size as the AOI, but they can also contain extent much bigger than the AOI. 

### It will generate two output files:

A csv file containing the following attributes per building polygon: building ID, maximum value of the height for all cell center points, minimum, average, sd, number of points, difference between the average height of the points and the height of the polygon. Statistics per building. 

The updated building height vector dataset with an added attribute for the difference in height between the average points height within a polygon and the building height. 

## How to run:
in main.py. replace the input and output files. input file paths can be a local path or an s3 link, the output paths should be locally. 
