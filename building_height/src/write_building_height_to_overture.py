import geopandas as gpd


def transfer_building_heights(overture_path, heights_path, output_path, output_format="GeoJSON"):
    """
    Transfers height values from one building dataset to another based on spatial intersections,
    explicitly handling column indexing to avoid misinterpretation and not using 'op' in sjoin.

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

    # Ensure columns are managed correctly after join
    if 'height_right' in joined_data.columns:
        joined_data['height'] = joined_data['height_right']
        joined_data.drop(columns=['height_right'], inplace=True)
    elif 'height_left' in joined_data.columns:
        joined_data['height'] = joined_data['height_left']
        joined_data.drop(columns=['height_left'], inplace=True)

    # Remove any index columns potentially misinterpreted
    joined_data.drop(columns=['index_right'], inplace=True)

    # Explicitly handle the unique identifier for each row
    joined_data['id'] = joined_data.apply(lambda row: row['id'] if 'id' in row else row.name, axis=1)

    # Fill missing height values
    joined_data['height'].fillna('', inplace=True)

    # Save the result to a file
    if output_format.lower() == "gpkg":
        joined_data.to_file(output_path, driver='GPKG')
    else:
        joined_data.to_file(output_path, driver='GeoJSON')

    print(f"Updated dataset saved to {output_path}. Columns: {joined_data.columns.tolist()}")


transfer_building_heights(r"C:\Users\zhuoyue.wang\Documents\Building_height_Monterrey\mty_clipped_overturebuilding3.geojson", r"C:\Users\zhuoyue.wang\Documents\Building_height_Monterrey/MTY_UTGLOBUS_upd.GPKG",
                          r"C:\Users\zhuoyue.wang\Documents\Building_height_Monterrey\mty_overture_height.geojson")

transfer_building_heights(r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\aoi1_overture1.gpkg", r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation/AMS_UTGLOBUS.GPKG",
                          r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\ams_overture_height.geojson")