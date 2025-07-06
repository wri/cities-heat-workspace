
## Structure

```
cities-heat-workspace/
├── config/                         
│   └── city_config.yaml             # City-specific data paths and settings
├── src/                             
│   ├── validation/                  
│   │   ├── building_height_path.py  
│   │   ├── building_footprint_path.py 
│   │   ├── shade_val_weighted_path.py 
│   │   └── utci_val_path.py         
│   ├── visualization/               
│   │   ├── buildings_viz.py         
│   │   ├── shade_viz.py             
│   │   └── utci_viz_path.py         
│   └── tests/                       # Test scripts (not used)
├── results/                         
│   ├── buildings/                   
│   ├── shade/                       
│   └── utci/                        
├── not_used/                        # Archived/unused files
└── requirements.txt                 # Python dependencies
```

### 2. Configure Cities
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

### 3. Run Validation Pipeline and Generate Visualisation

Update city name in the scripts' `main()`.  
Then run validation for each component.  

Afterwards, run visualisation for each component. The visualisation scripts use the `.csv` file created from the validation scripts.


## Analysis Components

### Building Height Validation
- **Metrics**: MAE, RMSE, R²
- **Outputs**: Scatter plots, histograms, error metrics CSV

### Building Footprint Validation
- **Metrics**: 
- **Outputs**: 

### Shade Validation
- **Metrics**: User's/Producer's accuracy, Kappa coefficient, confusion matrices
- **Outputs**: 
  - `results/shade/{city}/metrics/`: CSV files with accuracy statistics
  - `results/shade/{city}/graphs/`: Line plots and distribution charts

### UTCI Validation
- **Metrics**: MAE, RMSE, R², bias analysis across different shade conditions
- **Outputs**:
  - `results/utci/{city}/metrics/`: Statistical summaries
  - `results/utci/{city}/graphs/`: Scatter plots, line plots, error analysis


## Output Structure

```
results/
├── buildings/{city}/
│   ├── metrics/
│   │   ├── building_height_metrics.csv
│   │   └── building_footprint_accuracy.csv
│   └── graphs/
│       ├── height_scatterplot.png
│       └── height_histogram.png
├── shade/{city}/
│   ├── metrics/
│   │   ├── shade_accuracy_weighted.csv
│   │   ├── shade_confusion_matrix_all.csv
│   │   └── shade_kappa_all.csv
│   └── graphs/
│       ├── shade_area_distribution_*.png
│       └── shade_weighted_accuracy_*.png
└── utci/{city}/
    ├── metrics/
    │   └── utci_stats.csv
    └── graphs/
        ├── utci_scatter_All_1200.png
        ├── utci_line_mean_All.png
        └── utci_error_line_All.png
```

## Customization

### Adding New Cities
1. Add city configuration to `config/city_config.yaml`
2. Update city name in validation and visualisation scripts in `main()`
3. Ensure data paths are accessible in s3. If not, local paths can be used in scripts ending with `_path.py`.

### Modifying Sample Size
Change `SAMPLE_SIZE` in visualization scripts for scatter plots (default: 30,000 pixels).

