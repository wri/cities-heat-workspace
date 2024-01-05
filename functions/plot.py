#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, warnings
warnings.simplefilter('ignore')

import geopandas as gpd
import pandas as pd
import numpy as np
import xarray as xr
from rasterio import features

import geemap
import ee
#ee.Initialize()
import leafmap


# In[2]:


def plot_boxplot(boundary_path, tifffile_path, figdims = None, variable = 'band_data'):
    
    '''
    boundary_path: Path to geojson of area of interest
    tifffile_path: Path to TIFF file for which box plot is required. It can take input of other data types like NC file but variable name will have to be updated accordingly
    figdims: Figure dimensions of the box plot. Take a list as input as [x,y]. Default is None
    variable: Varaible name in xarray dataset for which box plot is to be plotted. Default is "band_data" 
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
    
    df = pd.DataFrame({'value' : np.array(xr_ds['band_data']).ravel(), 'zone' : np.array(zones_gdf_rasterized_xarr['zone']).ravel()})
    
    df = df[df['zone'] != 0].reset_index(drop = True)
    
    box_plot = df.boxplot(by='zone', figsize = figdims)
    
    return box_plot


# In[3]:


def plot_ee_image(ee_img, boundary_path, minmax, palette, display_name):
    
    '''
    ee_img: Earth Engine Image
    boundary_path: Path to geojson of area of interest. This sets the zoom in level.
    minmax: Minimum and maximum values for ploting the raster. Takes a list as input [min, max]
    palette: Color palette to be used for plotting the raster. Takes a list as input coresposnding to min, max and intermidiate values
    display_name: Display name of the data
    '''
    gdf = gpd.read_file(boundary_path)
    fc = ee.FeatureCollection(geemap.geopandas_to_ee(gdf))
    
    ee_img = ee_img.clip(fc)
    
    Map = geemap.Map()

    Map.zoom_to_gdf(gdf)

    Map.addLayer(ee_img,
                 {'min': minmax[0], 'max': minmax[1], 'palette': palette},
                 display_name)
    return Map


# In[4]:


def plot_ee_fc(boundary_path, zoom, display_name):
    
    '''
    boundary_path: Path to geojson of area of interest. This sets the zoom in level
    zoom: Zoom level of POV
    display_name: Display name of the data
    '''
    gdf = gpd.read_file(boundary_path).dissolve()
    cent = gdf.centroid
    
    Map = leafmap.Map(center = [cent.y[0], cent.x[0]], zoom = zoom)

    Map.add_geojson(boundary_path, layer_name = display_name)
                    
    return Map