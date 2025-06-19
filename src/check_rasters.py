import rasterio
import numpy as np
import typer

"""Todo:
1) read in rasters
 (later read in from .csv because there will be a lot of links)
2) check crs, size, boundaries, metadata, etc SPECIFICALLY FOR the files that have the same word until the first '_'
3) raise an error if 2 don't align
4) pass and say 'well aligned' if they all match"""

rasters = {
    "mty1_l_shadow_12": rasterio.open("https://wri-cities-heat.s3.us-east-1.amazonaws.com/MEX-Monterrey/output_local_v4/Shadow_2023_172_1200D.tif"),
    "mty1_l_shadow_15": rasterio.open("https://wri-cities-heat.s3.us-east-1.amazonaws.com/MEX-Monterrey/output_local_v4/Shadow_2023_172_1500D.tif"),
    "mty1_l_shadow_18": rasterio.open("https://wri-cities-heat.s3.us-east-1.amazonaws.com/MEX-Monterrey/output_local_v4/Shadow_2023_172_1800D.tif")
}

def check_raster(raster):
    for raster in rasters: 
        crs = rasters.rasterio.crs.get()



# for later: read all datasets from the excel file 

# check the metadata accordingly per city (and aoi), and raise an error if there's misalignment




# if __name__=="__main__":
#     main()