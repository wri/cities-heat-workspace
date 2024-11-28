from reproj_vector import crop_reproj_vector
from rasterize_gpkg import rasterize_gpkg
from smooth_dem import smooth_dem
from combine_dem_building_tifs import combine_dem_and_building

def create_global_building_dem():
    utglobus_path = ''
    utglobus_reproj_c_path = ''
    target_crs = "EPSG:32631"

    bbx = {"xmin": 120764.46,
           "ymin": 483845.95,
           "xmax": 122764.46,
           "ymax": 485845.95}

    #crop and reproject the UTBLOBUS to the aoi
    utglobus_cropped_utm = crop_reproj_vector(utglobus_path, utglobus_reproj_c_path, target_crs, bbx)

    #rasterize utglobus building
    utbuilding_tif_path = ''
    utbuilding_tif = rasterize_gpkg(utglobus_cropped_utm, utbuilding_tif_path)

    #smoothing nasadem
    input_nasadem = ''
    output_nasadem_smoothed = ''
    dem_smoothed = smooth_dem(input_nasadem, output_nasadem_smoothed, sigma=1)

    output_global_building_dem = ''
    combine_dem_and_building(dem_smoothed, utbuilding_tif_path, output_global_building_dem)