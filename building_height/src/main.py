from pre_processing_new import preprocessing
from processing import process_buildings

def main():
    '''
    input path from s3
    '''
    vector_path = 'https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/Building_height_validation/UTGLOBUS_Amsterdam.gpkg'
    raster_path = r'https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/Lidar_and_derived_data/DSM_2023_patch1.TIF'
    aoi_path = r'https://wri-cities-heat.s3.us-east-1.amazonaws.com/NLD-Amsterdam/aoi1_data/AOI_l.gpkg'

    output_csv_path = r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\AMS_UTGLOBUS.csv'
    output_vector_path = r'C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Height_validation\AMS_UTGLOBUS.GPKG'

    # preprocessing
    cropped_raster, transform, nodata_value, cropped_vector = preprocessing(aoi_path, raster_path, vector_path)

    # Process each building in the cropped vector data
    building_stats, avg_diff, stddev_diff, updated_vector = process_buildings(cropped_raster, cropped_vector, transform, nodata_value, output_csv_path, output_vector_path)

    # # Display the results
    # print("Building Statistics:")
    # for building_id, stats in building_stats.items():
    #     print(f"Building ID {building_id}: {stats}")
    #
    # print(f"\nOverall Performance:")
    print(f"Average Difference: {avg_diff}")
    print(f"Standard Deviation of Difference: {stddev_diff}")

    
if __name__ == "__main__":
    main()