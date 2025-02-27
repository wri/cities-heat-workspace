# cities-heat-workspace - Building Height Comparison

**A brief description of what this project does and who it's for:**
This project utilizes the Raster Cell Center Approach to compare building heights accurately within a specified area of interest. It is designed for urban planners, geospatial analysts, and researchers interested in urban morphology and building height discrepancies.

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
  - - **Size requirements**: Should at least cover the AOI but may extend beyond it.

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

To execute the project, follow these steps in `main.py`:

- **Replace the Input and Output File Paths**: Specify the paths for your input and output files. Input file paths can be either a local file path or an S3 link. However, ensure that output paths are local.
  
  Example of setting file paths in `main.py`:
  ```python
  input_path = "path/to/your/input/file.geojson"  # Local or S3 link
  output_path = "path/to/your/output/file.csv"    # Must be local
