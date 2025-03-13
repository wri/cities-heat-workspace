# cities-heat-workspace - Amsterdam CTCM Result Comparison: Local vs Global Data

In this branch of **`Amsterdam_comparison`**, the scripts are designed for **data preparation, preprocessing, and analysis of the CTCM results**. Instead of having a complete workflow with a main function, the scripts contain **separate functions** that are used **individually or in groups**.

## Data Preparation

### Combining DEM and Building Height Data
**`combine_dem_building.py`** takes two inputs: the **DEM** and **building rasters** and outputs a raster where the **building layer is placed on top of the DEM**.

The building height layers tested with this script were **rasterized vectors of buildings** or **rasterized point clouds from LiDAR data**. Cells without building height values are therefore written as **NoData**. The **DEM raster is first aligned and cropped** to the building raster layer and filled with **IDW interpolation** in case of empty cells. The building height values are finally placed on top of the DEM layer.

### Generating Global Data (Vector to Raster)
**`write_building_height_to_overture.py`** writes building height data from another gpkg (eg. UTGLOBUS) to the overture buildings. It joins the two tables. 
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

- **`check_raster_layers`** → Prints out the **CRS, resolution, origin, shape**, and **bounding box (BBX) in EPSG:4326** for inclusion in the **YML file of the CTCM setup**.

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


## Author
**Zhuoyue Wang**  
Email: [zhuoyueww@gmail.com]


