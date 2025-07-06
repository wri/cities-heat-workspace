#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, warnings
warnings.simplefilter('ignore')

import osmnx as ox
from enum import Enum

import geopandas as gpd


# In[3]:


def extract_osm_parks(boundary_path):
    
    '''
    boundary_path: Path to geojson of area of interest
    '''

    gdf = gpd.read_file(boundary_path)

    class OSMParks(Enum):
        leisure = ['park', 'nature_reserve']
        boundary = ['protected_area', 'national_park']

        @classmethod
        def to_dict(cls):
            return {e.name: e.value for e in cls}
    # get bbox
    bbox = gdf.total_bounds
    north, south, east, west = bbox[3],  bbox[1], bbox[0], bbox[2]

    # get osm tags
    osm_sites = ox.features_from_bbox(north, south, east, west, OSMParks.to_dict())

    # Drop points & lines
    osm_sites = osm_sites[osm_sites.geom_type != 'Point']
    osm_sites = osm_sites[osm_sites.geom_type != 'LineString']

    park = osm_sites.reset_index()[['osmid', 'name', 'geometry']]
    non_park = gpd.overlay(gdf[['geometry']], park.dissolve(), how = 'difference')   

    return park, non_park


# In[ ]:




