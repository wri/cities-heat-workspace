import geopandas as gpd
from pyproj import CRS, Transformer

def aoi_transformation(input_geopackage, output_geopackage = None, target_crs = "EPSG:28992"):

    gdf = gpd.read_file(input_geopackage)

    # Get the bounding box in EPSG:32631
    bbx_32631 = gdf.total_bounds  # [minx, miny, maxx, maxy]

    # Create a transformer from EPSG:32631 to EPSG:28992
    transformer = Transformer.from_crs(gdf.crs, target_crs, always_xy=True)

    # Transform the bounding box coordinates
    minx, miny = transformer.transform(bbx_32631[0], bbx_32631[1])
    maxx, maxy = transformer.transform(bbx_32631[2], bbx_32631[3])

    # Print the transformed bounding box
    print("Bounding box in EPSG:28992:", [minx, miny, maxx, maxy])

aoi_transformation(r'C:\Users\www\WRI-cif\AOI_2_utm.gpkg')
# [120764.45790837877, 485845.9530135797, 122764.4639352827, 487845.9552846286]