from crop_bbx import create_2km_bbox, crop_raster, crop_vector
from processing import process_buildings

def main():
    vector_path = r'C:\Users\www\WRI-cif\F_Eubucco_28992.gpkg'
    raster_path = r'C:\Users\www\WRI-cif\Validation_height\DSM_2023.TIF'

    output_csv_path = r'C:\Users\www\PycharmProjects\Height_Ams\data\result_Eubucco.csv'
    output_vector_path = r'C:\Users\www\PycharmProjects\Height_Ams\data\Eubucco_vector_updated.gpkg'
    # Example coordinates for the center of the bounding box (EPSG:28992 - Amersfoort / RD New)
    example_coordinates = (121764.46, 484845.95)

    # Create a bounding box (2km x 2km)
    bbox = create_2km_bbox(*example_coordinates)
    cropped_raster, transform, nodata_value = crop_raster(raster_path, bbox)
    cropped_vector = crop_vector(vector_path, bbox)

    # Process each building in the cropped vector data
    building_stats, avg_diff, stddev_diff, updated_vector = process_buildings(cropped_raster, cropped_vector, transform, nodata_value, output_csv_path)

    # # Display the results
    # print("Building Statistics:")
    # for building_id, stats in building_stats.items():
    #     print(f"Building ID {building_id}: {stats}")
    #
    # print(f"\nOverall Performance:")
    print(f"Average Difference: {avg_diff}")
    print(f"Standard Deviation of Difference: {stddev_diff}")

    updated_vector.to_file(output_vector_path, driver='GPKG')

    
if __name__ == "__main__":
    main()