#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os, warnings
warnings.simplefilter('ignore')

import geopandas as gpd
import pandas as pd
import numpy as np
import xarray as xr
from xrspatial import zonal_stats
from rasterio import features


# In[ ]:


def calculate_zonalstats(boundary_path, tifffile_path, variable = 'band_data'):
    
    '''
    zones_zones_gdf: Path to geojson of area of interest
    tifffile_path: Path to TIFF file for which zonal statistics is required. It can take input of other data types like NC file but variable name will have to be updated accordingly
    variable: varaible name in xarray dataset for which zonal statistics is to be computed. Default is "band_data"
    '''
    gdf = gpd.read_file(boundary_path)
    xr_ds = xr.open_dataset(tifffile_path)
    
    gdf = gdf.reset_index()
    zones_gdf = gdf[['geometry', 'index']]
    gdf['index'] = gdf['index'] + 1
    zones_gdf['index'] = zones_gdf['index'] + 1
    geom = zones_gdf[['geometry', 'index']].values.tolist()

    zones_gdf_rasterized = features.rasterize(geom, out_shape=[xr_ds.dims['y'],xr_ds.dims['x']], transform=xr_ds.rio.transform())

    zones_gdf_rasterized_xarr = xr_ds.squeeze().copy()

    zones_gdf_rasterized_xarr['zone'] = (('y', 'x'), zones_gdf_rasterized)
    
    zs = zonal_stats(zones_gdf_rasterized_xarr['zone'], xr_ds.squeeze()[variable])
    
    zs = zs[zs['zone'] != 0]
    
    zs = zs.rename({'zone':'index'}, axis = 1)
    
    zs_gdf = gdf.merge(zs, on = 'index')

    return zs_gdf


# In[ ]:




