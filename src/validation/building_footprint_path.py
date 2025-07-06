import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from pathlib import Path
import yaml
import pandas as pd
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import random

def open_local_raster(file_path):
    return rasterio.open(file_path)

def get_overlap_window(src1, src2):
    if src1.crs != src2.crs:
        bounds2 = transform_bounds(src2.crs, src1.crs, *src2.bounds)
    else:
        bounds2 = src2.bounds

    overlap_bounds = BoundingBox(
        max(src1.bounds.left, bounds2.left),
        max(src1.bounds.bottom, bounds2.bottom),
        min(src1.bounds.right, bounds2.right),
        min(src1.bounds.top, bounds2.top)
    )
    if (overlap_bounds.right <= overlap_bounds.left) or (overlap_bounds.top <= overlap_bounds.bottom):
        raise ValueError("No overlapping region between rasters.")

    window1 = from_bounds(*overlap_bounds, transform=src1.transform)
    window2 = from_bounds(*overlap_bounds, transform=src2.transform)
    return window1.round_offsets(), window2.round_offsets()


def shrink_window(window, n_pixels):
    return Window(
        window.col_off + n_pixels,
        window.row_off + n_pixels,
        window.width - 2 * n_pixels,
        window.height - 2 * n_pixels
    )


def calculate_basic_area_metrics(city, g_building, l_building, transform, output_dir):
    
    # calculate pixel area in square meters
    pixel_area = abs(transform.a * transform.e)
    
    # calculate total building areas
    global_building_area = np.sum(g_building) * pixel_area
    local_building_area = np.sum(l_building) * pixel_area
    
    # calculate absolute error
    error = global_building_area - local_building_area
    error_percentage = abs(error) / local_building_area * 100
    
    print(f"Basic Area Comparison:")
    print(f"   Global building area: {global_building_area:,.0f} m²")
    print(f"   Local building area: {local_building_area:,.0f} m²")
    print(f"   Error: {error:,.0f} m²")
    print(f"   Error percentage (%): {error_percentage:.2%}")
    
    # save basic area results
    area_results_df = pd.DataFrame({
        "City": [city],
        "Global_Building_Area_m2": [global_building_area],
        "Local_Building_Area_m2": [local_building_area],
            "Error_m2": [error],
        "Error_Percentage (%)": [error_percentage]
    })
    
    area_results_df.to_csv(output_dir / f"building_footprint_area_{city}.csv", index=False)
    
    return area_results_df


def validate_building_footprint(city, global_dsm_path, global_dem_path, local_dsm_path, local_dem_path, output_dir, n_points):
    
    with open_local_raster(global_dsm_path) as g_dsm, \
         open_local_raster(global_dem_path) as g_dem, \
         open_local_raster(local_dsm_path) as l_dsm, \
         open_local_raster(local_dem_path) as l_dem:

        # check alignment & crop to overlap
        if g_dsm.transform != l_dsm.transform or g_dsm.shape != l_dsm.shape:
            print("🟠 DSM mismatch. Cropping.")
            win_g_dsm, win_l_dsm = get_overlap_window(g_dsm, l_dsm)
            win_g_dsm = shrink_window(win_g_dsm, 10)
            win_l_dsm = shrink_window(win_l_dsm, 10)
        else:
            print("🟢 DSM aligned. Proceeding.")
            win_g_dsm = win_l_dsm = shrink_window(Window(0, 0, g_dsm.width, g_dsm.height), 10)

        # read raster data for the overlapping area
        g_dsm_data = g_dsm.read(1, window=win_g_dsm)
        g_dem_data = g_dem.read(1, window=win_g_dsm)
        l_dsm_data = l_dsm.read(1, window=win_l_dsm)
        l_dem_data = l_dem.read(1, window=win_l_dsm)

        # calculate building heights (DSM - DEM)
        g_height = g_dsm_data - g_dem_data
        l_height = l_dsm_data - l_dem_data

        # building footprint classification: building (1) vs non-building (0)
        g_building = (g_height > 0).astype(int)  # Global - prediction
        l_building = (l_height > 0).astype(int)  # Local - truth 

        # simple area comparison
        print("\n" + "="*50)
        print("SIMPLE AREA COMPARISON")
        print("="*50)
        area_results = calculate_basic_area_metrics(city, g_building, l_building, g_dsm.transform, output_dir)
        
        # point sampling
        print("\n" + "="*50)
        print("POINT SAMPLING")
        print("="*50)
        
        # drop random points in AOI 
        rows, cols = g_building.shape
        
        # generate random coordinates within the raster bounds
        random.seed(42)  # for reproducibility
        sample_rows = [random.randint(0, rows-1) for _ in range(n_points)] # (0,1,2,....rows-1)
        sample_cols = [random.randint(0, cols-1) for _ in range(n_points)]
        
        print(f"Sampling {n_points} random points for validation")
        
        # extract raster values at random points
        global_predictions = []
        local_truth = []
        
        for row, col in zip(sample_rows, sample_cols):
            # extract values at this point
            global_val = g_building[row, col]  # global prediction (0 or 1)
            local_val = l_building[row, col]   # local truth (0 or 1)
            
            global_predictions.append(global_val)
            local_truth.append(local_val)
        
        # convert to numpy arrays
        y_true = np.array(local_truth)   
        y_pred = np.array(global_predictions)  
        
        # calculate validation metrics
        conf_matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
        kappa = cohen_kappa_score(y_true, y_pred)
        
        # calculate accuracy metrics
        tn, fp, fn, tp = conf_matrix.ravel()
        
        # user's accuracy (precision): of predicted buildings, how many are actually buildings
        user_accuracy = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        
        # producer's accuracy (recall): of actual buildings, how many were detected
        producer_accuracy = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        # overall accuracy
        overall_accuracy = (tp + tn) / (tp + tn + fp + fn)
        
        # print validation results
        print(f" Building Footprint Validation Results:")
        print(f"   Total points sampled: {n_points}")
        print(f"   True buildings (LiDAR): {np.sum(y_true)}")
        print(f"   Predicted buildings (Global): {np.sum(y_pred)}")
        print(f"   Overall Accuracy: {overall_accuracy:.3f}")
        print(f"   User's Accuracy: {user_accuracy:.3f}")
        print(f"   Producer's Accuracy: {producer_accuracy:.3f}")
        print(f"   Kappa Coefficient: {kappa:.3f}")
        
        # save point sampling results to CSV
        point_results_df = pd.DataFrame({
            "City": [city],
            "Sample_Points": [n_points],
            "True_Buildings": [int(np.sum(y_true))],
            "Predicted_Buildings": [int(np.sum(y_pred))],
            "Overall_Accuracy": [overall_accuracy],
            "User_Accuracy": [user_accuracy],
            "Producer_Accuracy": [producer_accuracy],
            "Kappa": [kappa]
            # "True_Positives": [int(tp)],
            # "False_Positives": [int(fp)],
            # "False_Negatives": [int(fn)],
            # "True_Negatives": [int(tn)]
        })
        
        point_results_df.to_csv(output_dir / f"building_footprint_accuracy_{city}.csv", index=False)
        
        print(f"\n✅ Building footprint validation completed for {city}")
        print(f"   Results saved to: {output_dir.resolve()}")
        print("\nArea Comparison Summary:")
        print(area_results)
        print("\nPoint Sampling Summary:")
        print(point_results_df)


def main():
    with open("config/city_config.yaml", "r") as f:
        all_configs = yaml.safe_load(f)     

    # change the city name based on the city name in city_config.yaml   
    CITY_NAME = "RiodeJaneiro"

    if CITY_NAME not in all_configs:
        raise ValueError(f"{CITY_NAME} not found in config.")
    
    global_dsm_path = all_configs[CITY_NAME]['global_dsm_path']
    global_dem_path = all_configs[CITY_NAME]['global_dem_path']
    local_dsm_path = all_configs[CITY_NAME]['local_dsm_path']
    local_dem_path = all_configs[CITY_NAME]['local_dem_path']

    output_dir = Path(f"results/buildings/{CITY_NAME}/footprint/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    validate_building_footprint(CITY_NAME, global_dsm_path, global_dem_path, local_dsm_path, local_dem_path, output_dir, n_points = 500)


if __name__ == "__main__":
    main()
