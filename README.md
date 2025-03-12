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
This part of the analysis is designed to generate the statistics and differnece maps of the ctcm results. It does not include the process of running the model. 
Folder structure for the analysis: We can first create a main folder for the different scenarios for the same aoi. We take all the results from one run, including the three shadow maps (12, 15, 18), and four tmrt maps (12, 15, 18, average) to one subfolder, name it with the run name. The tif file names of the shadow or tmrt do not need to be changed. After all the subfolders are there under the main folder, the data is ready. You can find the example of folder structure below: 
![image](https://github.com/user-attachments/assets/6531fde7-0893-483a-b6d9-e9d21ffc13d8)
![image](https://github.com/user-attachments/assets/8a37ed7b-35f0-4c3e-bdd4-fa9f368db10c)
### Statistics (non-spatial)
shade_area_calculation.py is used to generate the non-spatial statistics of all the shadow result in the main folder. The output is an excel file that gathers all the shade area, percentage of the different shade types in the entire area, and the difference from the baseline. You could define the baseline run by changing the parameter: baseline_subfolder, which should correspond to the run name of the sub-folder. In the process, it also crops out the 500 meter edge on each side of all the rasters to avoid errors on the edge. This parameter can also be changed, and should not exceed the size of half of the shape for one side. 
To run it, give the input main folder path, which should follow the structure mentioned above. The output file should be xlsx format. edge buffer and baseline run can also be defined, but if not specified the default buffer is 500 meters and the baseline is none. 

### Overlaying rasters for the difference map
shade_compare.py generates the difference of the shadow maps by overlaying each one with the baseline run. Similar as above, it takes the main folder as input, and generates another folder with the same structure (without the baseline subfolder of course). Baseline run name and buffer size works as the non-spatial one. 

## Analysis of the ctcm result - UTCI
### Converting TMRT to UTCI
tmrt_to_utci.py converts tmrt result from ctcm to utci rasters. The input main folder works the same way as in shade, and it can be the same main folder containing shadow and tmrt in each subfolder. The met data should be the same txt file that was used to run ctcm, containing the following columns: col_names = [
        "iy", "id", "it", "imin", "qn", "qh", "qe", "qs", "qf",
        "U", "RH", "Tair", "press", "rain", "kdown", "snow", "ldown",
        "fcld", "wuh", "xsmd", "lai", "kdiff", "kdir", "wdir" ,"vpd"
    ] worth noticing that vpd is sometimes missing in the original met file. If missing, can pull the data directly from CIF and add this column. If vpd is not known still, it can be estimated from rh and air temp, but this script has not designed to do it yet. 
The output folder contains the same structure for each run, and in each subfolder the UTCI result for the different times. 
### Overlaying UTCI results for difference
utci_analysis.py can generate the statistics of the values of all the cells, and generate the overlay maps. They work the same way as in shade analysis. 
### Aggregating the UTCI difference based on resolution
tmrt_maps_agg.py generates the aggregation of UTCI difference maps by resolution and method. You can give a list of resolutions, for example [5, 10, 15], and another list of method like ["bilinear", "average"]. The input folder should be the UTCI difference maps from the last step, and in the output folder, it will first have a subfolder of the different method, and then the run names with the agregated maps inside. 
## Result visualization
### Printing the maps
print_map.py can be used to create jnp format images from the raster layers taken as input. There are several legend styles, including shade, temp, tree_height, building_height, utci, utci_diff_reclass. Shade and utci_diff_reclass show discrete legend, while the other legend types are all continuous legend. To use the utci_diff_reclass, it is required to generate this reclassfied utci difference with the another script first (reclass_for_printing_map.py). 
To run this script, it takes four parameters. Input folder should contain the same structure mentioned earlier, so subfolders with run name including the tif files. It also requires an inset map that should be prepared in advance, in png format. The output path is a folder, and the output folder will have the same structure as the input file. Last but not least, do't forget to specify the legend style. 
reclass_for_printing_map.py reclassifies the UTCI raster to bins. The bins for now are hardcoded still. 


# cities-heat-workspace - Amsterdam CTCM Result Comparison: Local vs Global Data

In this branch of **`Amsterdam_comparison`**, the scripts are designed for **data preparation, preprocessing, and analysis of the CTCM results**. Instead of having a complete workflow with a main function, the scripts contain **separate functions** that are used **individually or in groups**.

## Data Preparation

### Combining DEM and Building Height Data
**`combine_dem_building.py`** takes two inputs: the **DEM** and **building rasters** and outputs a raster where the **building layer is placed on top of the DEM**.

The building height layers tested with this script were **rasterized vectors of buildings** or **rasterized point clouds from LiDAR data**. Cells without building height values are therefore written as **NoData**. The **DEM raster is first aligned and cropped** to the building raster layer and filled with **IDW interpolation** in case of empty cells. The building height values are finally placed on top of the DEM layer.

### Generating Global Data (Vector to Raster)
**`rasterize_gpkg.py`** is used on **global building height datasets**, which are usually **GPKG files**, to rasterize them to a **user-defined resolution** and write the height of each building polygon to the rasterized cells. It also performs **cropping** if an **AOI GPKG** is provided, meaning that the **GPKG does not need to be preprocessed**.

**Parameters:**
- **`input_gpkg`** → Path to the **building height dataset**, which should contain an attribute called `height`.
- **`aoi_gpkg`** → Path to the **AOI file**. The bounding box of the AOI defines the extent of the output file.
- **`output_tif`** → Path to the **output TIF file**.
- **`resolution`** → (Optional) Grid resolution (default = **1m**).

### Generating Local Data (Point Cloud to Raster)
#### Extracting Tree Height from LiDAR
**`dbscan_test.py`** extracts **tree height** from **LiDAR data** in **LAZ format**. It is only used in **Amsterdam**, so there is **no guarantee** it will work for **CRS other than EPSG:28992**. 

**DBSCAN parameters:**
- **`min_area_m2`** → Minimum cluster area (default = **4 m²**).
- **`eps`** → Minimum distance between two clusters (default = **1**).
- **`min_samples`** → Minimum number of points per cluster (default = **50**).

#### Converting LiDAR Point Cloud to Raster
**`laz_to_tif.py`** writes the **height (Z-value)** of a **LAZ format point cloud file** to a raster. It creates cells with a **user-defined resolution** and writes the **highest Z-value** of all points within a cell to the TIF file.

**Parameters:**
- **`input_laz`** → Path to the **input LAZ file**.
- **`output_tif`** → Path to the **output raster file**.
- **`resolution`** → (Optional) Grid resolution (default = **1m**).

## Preprocessing
### Aligning Input Layers
The functions in **`check_raster_for_solweig.py`** align the input rasters and print out their information.

- **`align_rasters`** → Aligns the **transform, CRS, and shape** of input raster layers. The first file in the input path is used as a reference, so it does **not** have an output (use `None` for the first element in the output list). 
  - **Input:** List of raster file paths.
  - **Output:** List of aligned raster file paths (except the reference raster).

- **`check_raster_layers`** → Prints out the **CRS, resolution, origin, shape**, and **bounding box (BBX) in EPSG:4326** for inclusion in the **YAML file of the CTCM setup**.

## Analysis of the CTCM Result - Shadow
This part of the analysis **generates statistics and difference maps** of the CTCM results. It does **not** include running the model.

### Folder Structure for the Analysis
- A **main folder** is created for **different scenarios** for the **same AOI**.
- Each run’s results, including **three shadow maps (12:00, 15:00, 18:00)** and **four Tmrt maps (12:00, 15:00, 18:00, average)**, are stored in a **subfolder named after the run**.
- **Example Folder Structure:**
  ![image](https://github.com/user-attachments/assets/6531fde7-0893-483a-b6d9-e9d21ffc13d8)
  ![image](https://github.com/user-attachments/assets/8a37ed7b-35f0-4c3e-bdd4-fa9f368db10c)

### Statistics (Non-Spatial)
**`shade_area_calculation.py`** generates **non-spatial statistics** of all shadow results in the **main folder**. The output is an **Excel file** containing:
- **Total shade area**
- **Percentage of different shade types**
- **Difference from baseline**

**Additional Processing:**
- The script **crops out a 500m edge** from all rasters to avoid errors at the boundaries (default = `500m`, but adjustable).
- The **baseline run** can be specified using the `baseline_subfolder` parameter.

### Overlaying Rasters for Difference Maps
**`shade_compare.py`** generates **difference maps** by overlaying each **shadow map** with the **baseline run**. 
- Similar to **`shade_area_calculation.py`**, it takes the **main folder as input** and outputs a **new folder with the same structure**, excluding the baseline subfolder.

## Analysis of the CTCM Result - UTCI
### Converting Tmrt to UTCI
**`tmrt_to_utci.py`** converts **Tmrt results** from CTCM into **UTCI rasters**.

- The **main folder structure** follows the **same organization as the shadow analysis**.
- The script requires **meteorological data (`.txt` file)** with the following columns:
  ```text
  iy, id, it, imin, qn, qh, qe, qs, qf, U, RH, Tair, press, rain, kdown, snow, ldown,
  fcld, wuh, xsmd, lai, kdiff, kdir, wdir, vpd
  ```
- **`vpd` (vapor pressure deficit)** may be missing in some datasets. If missing, it can be extracted from **CIF** or estimated from **RH and air temperature**, but this script does not yet handle that process.

### Overlaying UTCI Results for Difference
**`utci_analysis.py`** generates:
- **Cell-wise UTCI statistics**
- **Overlay maps** showing differences

### Aggregating UTCI Differences Based on Resolution
**`tmrt_maps_agg.py`** aggregates **UTCI difference maps** by **resolution** and **method**.
- **Example Resolutions:** `[5, 10, 15]`
- **Example Methods:** `["bilinear", "average"]`
- **Output Structure:**
  ```
  ├── bilinear
  │   ├── run_name1
  │   ├── run_name2
  ├── average
      ├── run_name1
      ├── run_name2
  ```

## Result Visualization
### Printing Maps
**`print_map.py`** generates `.png` images from raster layers.

- **Supported Legend Styles:**
  - `shade`
  - `temp`
  - `tree_height`
  - `building_height`
  - `utci`
  - `utci_diff_reclass`

### Reclassifying UTCI for Visualization
**`reclass_for_printing_map.py`** creates **binned UTCI difference maps** for better visualization.

---

### Final Notes
This workflow ensures a **structured process for CTCM analysis**, with well-organized **data preparation, processing, and visualization tools**.


