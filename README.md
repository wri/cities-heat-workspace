# cities-heat-workspace - Building Height Comparison

This project utilizes the Raster Cell Center Approach to compare building heights accurately within a specified area of interest. 

## Description of the Method
The Raster Cell Center Approach enhances building height analysis by focusing on the geometric center of each raster cell and its presence within a building footprint polygon. This technique ensures that only relevant data contributes to height assessments, significantly enhancing the accuracy and relevance of measurements.

### Analysis Workflow
- **Check Cell Center Within Polygon**: Verify whether the center of each raster cell lies within a building footprint polygon.
- **Height List Compilation**: Compile a list of heights for raster cells whose centers are inside a polygon.
- **Average Height Calculation**: Calculate the average height from the compiled list for each building.
- **Comparison**: Compare the calculated average raster-derived height to the recorded building height in the vector data.

### Advantages
- **Precision**: Focuses solely on cell centers within building footprints to avoid biases introduced by rasterization.
- **Adaptability**: Suitable for buildings of various sizes, shapes, and footprints, offering broad applicability across different urban settings.
- **Ease of Use**: Does not require manual preprocessing of the input layers, streamlining the analysis process.

## Data Requirements
### Input Data
- **Area of Interest**:
  - **Recommended size**: 2km by 2km to manage processing time efficiently.
  - **Acceptable formats**: Any format readable by geopandas, such as GeoJSON or GeoPackage.
  - **CRS impact**: Determines the CRS used in calculations and results.

- **Vector Building Height Dataset**:
  - **Attribute requirements**: Must include an attribute for building height, potentially labeled as any of the following:
    - 'height', 'Height', 'heights', 'Heights'
    - 'building heights', 'Building heights'
    - 'building_height', 'Building_height'
    - 'building_heights', 'Building_heights'
  - **Size requirements**: Should at least cover the AOI but may extend beyond it.

- **DSM Raster Layer**:
  - **Resolution/CRS**: Can be in any resolution or CRS.
  - **Size requirements**: Should at least cover the AOI but may extend beyond it.

### Output Files
- **CSV File**:
  - **Contents**: Includes building ID, maximum, minimum, average, standard deviation, number of points, and the difference between the average height of the points and the polygon's height.
  - **Usage**: Facilitates detailed statistical analysis per building.

- **Updated Building Height Vector Dataset**:
  - **New attribute**: Contains a newly added attribute detailing the difference in height between the raster-derived average and the vector-specified building height.

## How to Run

To execute the project, you will need to set up your input and output file paths in `main.py`. Below is an example of how to specify these paths:

```python
# Path to the vector data file
vector_path = 'path/to/your/vector/data.gpkg'

# Path to the raster data file
raster_path = 'path/to/your/raster/data.tif'

# Path to the area of interest file
aoi_path = 'path/to/your/area/of/interest.geojson'

# Output paths for the results
output_csv_path = 'path/to/your/statistics.csv'
output_vector_path = 'path/to/your/updated_building_height.gpkg'
