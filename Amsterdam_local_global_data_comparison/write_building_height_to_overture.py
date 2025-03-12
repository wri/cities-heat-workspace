import geopandas as gpd
import pandas as pd

def transfer_building_heights(overture_path, heights_path, output_path, output_format="GeoJSON"):
    """
    Transfers height values from one building dataset to another based on spatial intersections,
    explicitly handling column indexing to avoid misinterpretation and ensuring numeric type for height.

    Parameters:
        overture_path (str): Path to the building overture layer file.
        heights_path (str): Path to the building height layer file.
        output_path (str): Path to save the updated overture layer.
        output_format (str): Format of the output file ("GeoJSON" or "GPKG").
    """
    # Load the datasets
    building_overture = gpd.read_file(overture_path)
    building_heights = gpd.read_file(heights_path)

    # Ensure both GeoDataFrames are using the same coordinate reference system
    building_heights = building_heights.to_crs(building_overture.crs)

    # Perform spatial join - transferring height values directly during the join
    joined_data = gpd.sjoin(building_overture, building_heights[['geometry', 'height']], how='left')

    # Handle height columns after join and convert them to float
    height_column = 'height_right' if 'height_right' in joined_data.columns else 'height_left'
    joined_data['height'] = pd.to_numeric(joined_data[height_column], errors='coerce')
    joined_data.drop(columns=[col for col in joined_data.columns if col.endswith('_right') or col.endswith('_left')], inplace=True)

    # Remove any index columns potentially misinterpreted
    joined_data.drop(columns=['index_right', 'index_left'], errors='ignore', inplace=True)

    # Explicitly handle the unique identifier for each row
    if 'id' not in joined_data.columns:
        joined_data['id'] = joined_data.index

    # Fill missing height values with a specific value or leave as NaN for later handling
    joined_data['height'].fillna(value=0, inplace=True)  # You can change 0 to any other number or method to handle NaNs

    # Save the result to a file
    if output_format.lower() == "gpkg":
        joined_data.to_file(output_path, driver='GPKG')
    else:
        joined_data.to_file(output_path, driver='GeoJSON')

    print(f"Updated dataset saved to {output_path}. Columns: {joined_data.columns.tolist()}")


# transfer_building_heights(r"C:\Users\zhuoyue.wang\Documents\Building_height_Monterrey\mty_clipped_overturebuilding3.geojson", r"C:\Users\zhuoyue.wang\Documents\Building_height_Monterrey/MTY_UTGLOBUS_upd.GPKG",
#                           r"C:\Users\zhuoyue.wang\Documents\Building_height_Monterrey\mty_overture_height1.geojson")

transfer_building_heights(r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\aoi1_overture1.gpkg", r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation/AMS_UTGLOBUS.GPKG",
                          r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\ams_overture_height1.geojson")