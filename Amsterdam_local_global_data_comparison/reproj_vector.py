import geopandas as gpd
from shapely.geometry import box
from pyproj import Transformer

# Load the GeoPackage (replace 'input.gpkg' with the actual file path)
# input_gpkg = r'C:\Users\www\PycharmProjects\Height_Ams\data\3dglobpf_vector_updated.gpkg'
# output_gpkg = r'C:\Users\www\WRI-cif\Validation_height\4326transform\3dglobpf_4326.gpkg'

def crop_reproj_vector (input_gpkg, output_gpkg, target_crs, bbx):
    """
    Crop and reproject a vector file to a target CRS and bounding box.

    Parameters:
        input_gpkg (str): Path to the input GeoPackage file.
        output_gpkg (str): Path to save the output GeoPackage file.
        target_crs (str or int): Target CRS to reproject to (e.g., 'EPSG:4326').
        bbx (dict): Bounding box in the original CRS with keys 'xmin', 'ymin', 'xmax', 'ymax'.

    Returns:
        cropped and reprojected gpkg
    """
    # Load the input GeoPackage
    gdf = gpd.read_file(input_gpkg)

    # Reproject the bounding box to the target CRS
    transformer = Transformer.from_crs(gdf.crs, target_crs, always_xy=True)
    xmin, ymin = transformer.transform(bbx['xmin'], bbx['ymin'])
    xmax, ymax = transformer.transform(bbx['xmax'], bbx['ymax'])

    # Reproject the GeoDataFrame to the target CRS
    gdf_reproj = gdf.to_crs(target_crs)

    # Crop the GeoDataFrame using the reprojected bounding box
    cropped_gdf = gdf_reproj.cx[xmin:xmax, ymin:ymax]

    # Save the cropped and reprojected GeoDataFrame to a GeoPackage
    cropped_gdf.to_file(output_gpkg, layer='transformed_layer', driver='GPKG')

    return cropped_gdf


target_crs = "EPSG:32631"  # Target CRS to reproject to

# Bounding box in EPSG:28992
bbx = { "xmin": 120764.46,
        "ymin": 483845.95,
        "xmax": 122764.46,
        "ymax": 485845.95}

crop_reproj_vector(input_gpkg, output_gpkg, target_crs, bbx)