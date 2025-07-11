# cities-heat-workspace
## *work in progress, constantly being updated*
# Data Validation

## Structure

```
cities-heat-workspace/
├── config/                         
│   └── city_config.yaml             # City-specific data paths and settings
├── src/                             
│   ├── preprocessing/               
│   │   └── resample_rasters.py      # Resample rasters to 20m resolution
│   ├── validation/                  
│   │   ├── building_height_path.py  
│   │   ├── building_footprint_path.py 
│   │   ├── shade_val_weighted_path.py 
│   │   ├── shade_val_masks.py       # Mask-based shade validation (1m/20m)
│   │   ├── utci_val_path.py         
│   │   └── utci_val_masks.py        # Mask-based UTCI validation (1m/20m)
│   ├── visualization/               
│   │   ├── building_height_viz.py         
│   │   ├── shade_viz.py             
│   │   ├── shade_viz_masks.py       # Mask-based shade visualization (1m/20m)
│   │   ├── utci_viz_path.py         
│   │   └── utci_viz_masks.py        # Mask-based UTCI visualization (1m/20m)
│   └── tests/                       # Test scripts (not used)
├── data/                            
│   └── resampled/                   # 20m resampled raster data
│       └── {city}/                  
│           ├── shade/               
│           ├── utci/                
│           └── masks/               
├── results/                         
│   ├── buildings/                   
│   ├── shade/                       
│   └── utci/                        
├── not_used/                        # Archived/unused files
└── requirements.txt                 # Python dependencies
```

### 1. Configure Cities
Edit `config/city_config.yaml` to add city's data paths:  
*The ones using local paths end with `_path` in the name.* 

```yaml
CityName:
  # Building data paths 
  building_height_local_paths: ["/path/to/local/height.tif"]
  building_height_global_paths: ["/path/to/global/height.tif"]
  
  # Shade data paths
  shade_local_paths: ["/path/to/local/shade_1200.tif", ...]
  shade_global_paths: ["/path/to/global/shade_1200.tif", ...]
  
  # UTCI data paths
  utci_local_paths: ["/path/to/local/utci_1200.tif", ...]
  utci_global_paths: ["/path/to/global/utci_1200.tif", ...]
```

### 2. Run Validation Pipeline and Generate Visualisation

Update city name in the scripts' `main()` function.  
Then run validation for each component.  

Afterwards, run visualisation for each component. The visualisation scripts use the `.csv` file created from the validation scripts.


## Analysis Components

### Building Height Validation
- **Script**: `src/validation/building_height_path.py`
- **Metrics**: MAE, RMSE, R², Standard Deviation (with Z-score filtering ±3)
- **Outputs**: 
  - `results/buildings/{city}/height/metrics/`: CSV files with filtered and unfiltered metrics
  - `results/buildings/{city}/height/graphs/`: Histogram, scatter plot

### Building Footprint Validation
- **Script**: `src/validation/building_footprint_path.py`
- **Metrics**: 
  - Area comparison: Absolute error between total building areas
  - Point sampling: Overall/User's/Producer's accuracy, Kappa coefficient, confusion matrix
- **Outputs**: 
  - `building_footprint_area_{city}.csv`: Area comparison results
  - `building_footprint_accuracy_{city}.csv`: Point sampling validation results

### Shade Validation
- **Script**: `src/validation/shade_val_weighted_path.py`
- **Metrics**: User's/Producer's accuracy, Kappa coefficient, confusion matrices (weighted by area)
- **Resolution**: 1m, 20m
- **Outputs**: 
  - `results/shade/{city}/metrics/`: CSV files with accuracy statistics
  - `results/shade/{city}/graphs/`: Shade area distribution charts, Weighted accuracy plots

### UTCI Validation
- **Script**: `src/validation/utci_val_path.py`
- **Metrics**: MAE, RMSE, R², bias analysis across different shade conditions
- **Resolution**: 1m, 20m
- **Outputs**:
  - `results/utci/{city}/metrics/`: Statistical summaries by shade type
  - `results/utci/{city}/graphs/`: Scatter plots, line plots, error analysis by shade type

## Output Structure

```
results/
├── buildings/{city}/
│   ├── footprint/
│   │   └── metrics/
│   │       ├── building_footprint_area_{city}.csv       
│   │       ├── building_footprint_accuracy_{city}.csv     
│   │       └── building_footprint_confusion_matrix_{city}.csv 
│   └── height/
│       ├── metrics/
│       │   ├── building_height_metrics_filtered_by_zscore.csv
│       │   └── building_height_metrics_unfiltered.csv
│       └── graphs/
│           ├── height_error_histogram_zscore_filtered.png
│           └── height_scatterplot_zscore_filtered.png
├── shade/{city}/
│   ├── metrics/                     # Whole area validation
│   │   ├── shade_accuracy_weighted_{city}.csv
│   │   ├── shade_confusion_matrix_all_{city}.csv
│   │   └── shade_kappa_all_{city}.csv
│   ├── graphs/                      # Whole area visualization
│   │   ├── shade_area_distribution_percentage_{time}.png 
│   │   ├── shade_weighted_accuracy_{time}.png
│   │   ├── shade_difference_by_type_raw.png
│   │   └── ...
│   ├── 20m/                         # 20m resolution results
│   │   └── {mask}/                  # Mask-based validation (pedestrian, LULC)
│   │       ├── metrics/
│   │       │   ├── shade_accuracy_weighted_{city}_{mask}.csv
│   │       │   ├── shade_confusion_matrix_all_{city}_{mask}.csv
│   │       │   └── shade_kappa_all_{city}_{mask}.csv
│   │       └── graphs/
│   │           ├── shade_area_distribution_percentage_{time}_{mask}.png
│   │           ├── shade_weighted_accuracy_{time}_{mask}.png
│   │           └── ...
│   └── {mask}/                      # 1m resolution mask-based results
│       ├── metrics/
│       │   ├── shade_accuracy_weighted_{city}_{mask}.csv
│       │   ├── shade_confusion_matrix_all_{city}_{mask}.csv
│       │   └── shade_kappa_all_{city}_{mask}.csv
│       └── graphs/
│           ├── shade_area_distribution_percentage_{time}_{mask}.png
│           ├── shade_weighted_accuracy_{time}_{mask}.png
│           └── ...
└── utci/{city}/
    ├── metrics/                     # Whole area validation
    │   └── utci_stats_{city}.csv
    ├── graphs/                      # Whole area visualization
    │   ├── utci_scatter_All_1200.png
    │   ├── utci_line_mean_All.png
    │   ├── utci_error_line_All.png       
    │   └── ...
    ├── 20m/                         # 20m resolution results
    │   └── {mask}/                  # Mask-based validation (pedestrian, LULC)
    │       ├── metrics/
    │       │   └── utci_stats_{city}_{mask}.csv
    │       └── graphs/
    │           ├── utci_scatter_All_1200_{mask}.png
    │           ├── utci_line_mean_All_{mask}.png
    │           └── ...
    └── {mask}/                      # 1m resolution mask-based results
        ├── metrics/
        │   └── utci_stats_{city}_{mask}.csv
        └── graphs/
            ├── utci_scatter_All_1200_{mask}.png
            ├── utci_line_mean_All_{mask}.png
            └── ...
```

## Customization

### Adding New Cities
1. Add city configuration to `config/city_config.yaml`
2. Update city name in validation and visualisation scripts in `main()`
3. Ensure data paths are accessible in s3. If not, local paths can be used in scripts ending with `_path.py`.

### Modifying Sample Size
Change `SAMPLE_SIZE` in visualization scripts for scatter plots (default: 30,000 pixels).

