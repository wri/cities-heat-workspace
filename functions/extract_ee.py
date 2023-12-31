#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, warnings
warnings.simplefilter('ignore')
import ipyleaflet
import time


import ee
#ee.Authenticate()
#ee.Initialize()
import wxee
wxee.Initialize()
import geemap


import requests
import boto3
from google.cloud import storage

import pandas as pd
import numpy as np
import rasterio
from rasterio import features
import geopandas as gpd
import xarray as xr
from xrspatial import zonal_stats
import glob


# In[2]:


def extract_ee_data(product_path, band_name, band_scale, band_offset, boundary_path, start_date, end_date, reducer = 'mean'):
    
    '''
    product_path: Link to GEE product
    band_name: Name of required band as mentioned in GEE product
    band_scale: Scale factor for the selected band as mentioned in GEE or as per requirement
    band_offset: Offset factor for the selected band as mentioned in GEE or as per requirement
    boundary_path: Path to geojson of area of interest
    start_date: Starting date of period for which data is required
    end_date: Ending date of period for which data is required
    reducer: The type reducer for time series image collection. Can choose between mean, max and min. Default is mean.
    '''
    
    gdf = gpd.read_file(boundary_path)
    fc = ee.FeatureCollection(geemap.geopandas_to_ee(gdf))
    
    if reducer == 'mean':
        ic = ee.ImageCollection(product_path).filterBounds(fc).filterDate(start_date, end_date).select(band_name).reduce(ee.Reducer.mean())
        
    elif reducer == 'max':
        ic = ee.ImageCollection(product_path).filterBounds(fc).filterDate(start_date, end_date).select(band_name).reduce(ee.Reducer.max())
        
    elif reducer == 'min':
        ic = ee.ImageCollection(product_path).filterBounds(fc).filterDate(start_date, end_date).select(band_name).reduce(ee.Reducer.min())
    
    def convert_ic(raw):
        converted = raw.multiply(band_scale).add(band_offset)
        return converted
    
    img = ee.ImageCollection(ic).map(convert_ic)
    img = img.toBands()

    return img


# In[3]:


def extract_modisterralst(boundary_path, start_date, end_date):
    
    '''
    boundary_path: Path to geojson of area of interest
    start_date: Starting date of period for which data is required
    end_date: Ending date of period for which data is required
    '''
    
    product_path = 'MODIS/006/MYD11A1'
    day_band_name = 'LST_Day_1km'
    night_band_name = 'LST_Night_1km'
    band_scale = 0.02
    KtoC = -273.15
    
    lst_day_ic = extract_ee_data(product_path, day_band_name, band_scale, KtoC, boundary_path, start_date, end_date)
    lst_night_ic = extract_ee_data(product_path, night_band_name, band_scale, KtoC, boundary_path, start_date, end_date)
    
    return (lst_day_ic, lst_night_ic)


# In[4]:


def extract_landsat8_lst(boundary_path, start_date, end_date):
    #  METHODS TO CALCULATE MEAN LST MOSAIC FOR HOTTEST PERIOD USING LANDSAT
    # ee.Authenticate()
    # ee.Initialize()

    """"
    boundary_path: Path to geojson of area of interest
    start_date: Starting date of period for which data is required
    end_date: Ending date of period for which data is required
    
    *****
    Derived from
    LSTfun = require('users/sofiaermida/landsat_smw_lst:modules/SMWalgorithm.js')
    'Author': Sofia Ermida (sofia.ermida@ipma.pt; @ermida_sofia)

    This code is free and open.
    By using this code and any data derived with it,
    you agree to cite the following reference
    'in any publications derived from them':
    Ermida, S.L., Soares, P., Mantas, V., Göttsche, F.-M., Trigo, I.F., 2020.
        Google Earth Engine open-source code for Land Surface Temperature estimation from the Landsat series.
        'Remote Sensing, 12 (9), 1471; https://doi.org/10.3390/rs12091471
    """

    COLLECTION = ee.Dictionary({
        'L4': {
            'TOA': ee.ImageCollection('LANDSAT/LT04/C02/T1_TOA'),
            'SR': ee.ImageCollection('LANDSAT/LT04/C02/T1_L2'),
            'TIR': ['B6', ],
            'VISW': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL']
        },
        'L5': {
            'TOA': ee.ImageCollection('LANDSAT/LT05/C02/T1_TOA'),
            'SR': ee.ImageCollection('LANDSAT/LT05/C02/T1_L2'),
            'TIR': ['B6', ],
            'VISW': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL']
        },
        'L7': {
            'TOA': ee.ImageCollection('LANDSAT/LE07/C02/T1_TOA'),
            'SR': ee.ImageCollection('LANDSAT/LE07/C02/T1_L2'),
            'TIR': ['B6_VCID_1', 'B6_VCID_2'],
            'VISW': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL']
        },
        'L8': {
            'TOA': ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA'),
            'SR': ee.ImageCollection('LANDSAT/LC08/C02/T1_L2'),
            'TIR': ['B10', 'B11'],
            'VISW': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'QA_PIXEL']
        }
    })

    def NDVIaddBand(landsat):
        def wrap(image):
            # choose bands
            nir = ee.String(ee.Algorithms.If(landsat == 'L8', 'SR_B5', 'SR_B4'))
            red = ee.String(ee.Algorithms.If(landsat == 'L8', 'SR_B4', 'SR_B3'))

            # compute NDVI
            return image.addBands(image.expression('(nir-red)/(nir+red)', {
                'nir': image.select(nir).multiply(0.0000275).add(-0.2),
                'red': image.select(red).multiply(0.0000275).add(-0.2)
            }).rename('NDVI'))

        return wrap

    def FVCaddBand(landsat):
        def wrap(image):
            ndvi = image.select('NDVI')

            # Compute FVC
            fvc = image.expression('((ndvi-ndvi_bg)/(ndvi_vg - ndvi_bg))**2',
                                   {'ndvi': ndvi, 'ndvi_bg': 0.2, 'ndvi_vg': 0.86})
            fvc = fvc.where(fvc.lt(0.0), 0.0)
            fvc = fvc.where(fvc.gt(1.0), 1.0)

            return image.addBands(fvc.rename('FVC'))

        return wrap

    def NCEP_TPWaddBand(image):
        # first select the day of interest
        date = ee.Date(image.get('system:time_start'))
        year = ee.Number.parse(date.format('yyyy'))
        month = ee.Number.parse(date.format('MM'))
        day = ee.Number.parse(date.format('dd'))
        date1 = ee.Date.fromYMD(year, month, day)
        date2 = date1.advance(1, 'days')

        # function compute the time difference from landsat image
        def datedist(image):
            return image.set('DateDist',
                             ee.Number(image.get('system:time_start')) \
                             .subtract(date.millis()).abs())

        # load atmospheric data collection
        TPWcollection = ee.ImageCollection('NCEP_RE/surface_wv') \
            .filter(ee.Filter.date(date1.format('yyyy-MM-dd'), date2.format('yyyy-MM-dd'))) \
            .map(datedist)

        # select the two closest model times
        closest = (TPWcollection.sort('DateDist')).toList(2)

        # check if there is atmospheric data in the wanted day
        # if not creates a TPW image with non-realistic values
        # these are then masked in the SMWalgorithm function (prevents errors)
        tpw1 = ee.Image(ee.Algorithms.If(closest.size().eq(0), ee.Image.constant(-999.0),
                                         ee.Image(closest.get(0)).select('pr_wtr')))
        tpw2 = ee.Image(ee.Algorithms.If(closest.size().eq(0), ee.Image.constant(-999.0),
                                         ee.Algorithms.If(closest.size().eq(1), tpw1,
                                                          ee.Image(closest.get(1)).select('pr_wtr'))))

        time1 = ee.Number(ee.Algorithms.If(closest.size().eq(0), 1.0,
                                           ee.Number(tpw1.get('DateDist')).divide(ee.Number(21600000))))
        time2 = ee.Number(ee.Algorithms.If(closest.size().lt(2), 0.0,
                                           ee.Number(tpw2.get('DateDist')).divide(ee.Number(21600000))))

        tpw = tpw1.expression('tpw1*time2+tpw2*time1',
                              {'tpw1': tpw1,
                               'time1': time1,
                               'tpw2': tpw2,
                               'time2': time2
                               }).clip(image.geometry())

        # SMW coefficients are binned by TPW values
        # find the bin of each TPW value
        pos = tpw.expression(
            "value = (TPW>0 && TPW<=6) ? 0" + \
            ": (TPW>6 && TPW<=12) ? 1" + \
            ": (TPW>12 && TPW<=18) ? 2" + \
            ": (TPW>18 && TPW<=24) ? 3" + \
            ": (TPW>24 && TPW<=30) ? 4" + \
            ": (TPW>30 && TPW<=36) ? 5" + \
            ": (TPW>36 && TPW<=42) ? 6" + \
            ": (TPW>42 && TPW<=48) ? 7" + \
            ": (TPW>48 && TPW<=54) ? 8" + \
            ": (TPW>54) ? 9" + \
            ": 0", {'TPW': tpw}) \
            .clip(image.geometry())

        # add tpw to image as a band
        withTPW = (image.addBands(tpw.rename('TPW'), ['TPW'])).addBands(pos.rename('TPWpos'), ['TPWpos'])

        return withTPW

    # get ASTER emissivity
    aster = ee.Image("NASA/ASTER_GED/AG100_003")

    # get ASTER FVC from NDVI
    aster_ndvi = aster.select('ndvi').multiply(0.01)

    aster_fvc = aster_ndvi.expression('((ndvi-ndvi_bg)/(ndvi_vg - ndvi_bg))**2',
                                      {'ndvi': aster_ndvi, 'ndvi_bg': 0.2, 'ndvi_vg': 0.86})
    aster_fvc = aster_fvc.where(aster_fvc.lt(0.0), 0.0)
    aster_fvc = aster_fvc.where(aster_fvc.gt(1.0), 1.0)

    # bare ground emissivity functions for each band
    def ASTERGEDemiss_bare_band10(image):
        return image.expression('(EM - 0.99*fvc)/(1.0-fvc)', {
            'EM': aster.select('emissivity_band10').multiply(0.001),
            'fvc': aster_fvc}) \
            .clip(image.geometry())

    def ASTERGEDemiss_bare_band11(image):
        return image.expression('(EM - 0.99*fvc)/(1.0-fvc)', {
            'EM': aster.select('emissivity_band11').multiply(0.001),
            'fvc': aster_fvc}) \
            .clip(image.geometry())

    def ASTERGEDemiss_bare_band12(image):
        return image.expression('(EM - 0.99*fvc)/(1.0-fvc)', {
            'EM': aster.select('emissivity_band12').multiply(0.001),
            'fvc': aster_fvc}) \
            .clip(image.geometry())

    def ASTERGEDemiss_bare_band13(image):
        return image.expression('(EM - 0.99*fvc)/(1.0-fvc)', {
            'EM': aster.select('emissivity_band13').multiply(0.001),
            'fvc': aster_fvc}) \
            .clip(image.geometry())

    def ASTERGEDemiss_bare_band14(image):
        return image.expression('(EM - 0.99*fvc)/(1.0-fvc)', {
            'EM': aster.select('emissivity_band14').multiply(0.001),
            'fvc': aster_fvc}) \
            .clip(image.geometry())

    def EMaddBand(landsat, use_ndvi):
        def wrap(image):
            c13 = ee.Number(ee.Algorithms.If(landsat == 'L4', 0.3222,
                                             ee.Algorithms.If(landsat == 'L5', -0.0723,
                                                              ee.Algorithms.If(landsat == 'L7', 0.2147,
                                                                               0.6820))))
            c14 = ee.Number(ee.Algorithms.If(landsat == 'L4', 0.6498,
                                             ee.Algorithms.If(landsat == 'L5', 1.0521,
                                                              ee.Algorithms.If(landsat == 'L7', 0.7789,
                                                                               0.2578))))
            c = ee.Number(ee.Algorithms.If(landsat == 'L4', 0.0272,
                                           ee.Algorithms.If(landsat == 'L5', 0.0195,
                                                            ee.Algorithms.If(landsat == 'L7', 0.0059,
                                                                             0.0584))))

            # get ASTER emissivity
            # convolve to Landsat band
            emiss_bare = image.expression('c13*EM13 + c14*EM14 + c', {
                'EM13': ASTERGEDemiss_bare_band13(image),
                'EM14': ASTERGEDemiss_bare_band14(image),
                'c13': ee.Image(c13),
                'c14': ee.Image(c14),
                'c': ee.Image(c)
            })

            # compute the dynamic emissivity for Landsat
            EMd = image.expression('fvc*0.99+(1-fvc)*em_bare',
                                   {'fvc': image.select('FVC'), 'em_bare': emiss_bare})

            # compute emissivity directly from ASTER
            # without vegetation correction
            # get ASTER emissivity
            aster = ee.Image("NASA/ASTER_GED/AG100_003") \
                .clip(image.geometry())
            EM0 = image.expression('c13*EM13 + c14*EM14 + c', {
                'EM13': aster.select('emissivity_band13').multiply(0.001),
                'EM14': aster.select('emissivity_band14').multiply(0.001),
                'c13': ee.Image(c13),
                'c14': ee.Image(c14),
                'c': ee.Image(c)
            })

            # select which emissivity to output based on user selection
            EM = ee.Image(ee.Algorithms.If(use_ndvi, EMd, EM0))

            return image.addBands(EM.rename('EM'))

        return wrap

    def get_lookup_table(fc, prop_1, prop_2):
        reducer = ee.Reducer.toList().repeat(2)
        lookup = fc.reduceColumns(reducer, [prop_1, prop_2])
        return ee.List(lookup.get('list'))

    def LSTaddBand(landsat):
        def wrap(image):
            # coefficients for the Statistical Mono-Window Algorithm
            coeff_SMW_L8 = ee.FeatureCollection([
                ee.Feature(None, {'TPWpos': 0, 'A': 0.9751, 'B': -205.8929, 'C': 212.7173}),
                ee.Feature(None, {'TPWpos': 1, 'A': 1.0090, 'B': -232.2750, 'C': 230.5698}),
                ee.Feature(None, {'TPWpos': 2, 'A': 1.0541, 'B': -253.1943, 'C': 238.9548}),
                ee.Feature(None, {'TPWpos': 3, 'A': 1.1282, 'B': -279.4212, 'C': 244.0772}),
                ee.Feature(None, {'TPWpos': 4, 'A': 1.1987, 'B': -307.4497, 'C': 251.8341}),
                ee.Feature(None, {'TPWpos': 5, 'A': 1.3205, 'B': -348.0228, 'C': 257.2740}),
                ee.Feature(None, {'TPWpos': 6, 'A': 1.4540, 'B': -393.1718, 'C': 263.5599}),
                ee.Feature(None, {'TPWpos': 7, 'A': 1.6350, 'B': -451.0790, 'C': 268.9405}),
                ee.Feature(None, {'TPWpos': 8, 'A': 1.5468, 'B': -429.5095, 'C': 275.0895}),
                ee.Feature(None, {'TPWpos': 9, 'A': 1.9403, 'B': -547.2681, 'C': 277.9953})
            ]);
            # Select algorithm coefficients
            coeff_SMW = ee.FeatureCollection(coeff_SMW_L8)

            # Create lookups for the algorithm coefficients
            A_lookup = get_lookup_table(coeff_SMW, 'TPWpos', 'A');
            B_lookup = get_lookup_table(coeff_SMW, 'TPWpos', 'B');
            C_lookup = get_lookup_table(coeff_SMW, 'TPWpos', 'C');

            # Map coefficients to the image using the TPW bin position
            A_img = image.remap(A_lookup.get(0), A_lookup.get(1), 0.0, 'TPWpos').resample('bilinear');
            B_img = image.remap(B_lookup.get(0), B_lookup.get(1), 0.0, 'TPWpos').resample('bilinear');
            C_img = image.remap(C_lookup.get(0), C_lookup.get(1), 0.0, 'TPWpos').resample('bilinear');

            # select TIR band
            tir = ee.String(ee.Algorithms.If(landsat == 'L8', 'B10',
                                             ee.Algorithms.If(landsat == 'L7', 'B6_VCID_1',
                                                              'B6')));
            # compute the LST
            lst = image.expression(
                'A*Tb1/em1 + B/em1 + C',
                {'A': A_img,
                 'B': B_img,
                 'C': C_img,
                 'em1': image.select('EM'),
                 'Tb1': image.select(tir)
                 }).updateMask(image.select('TPW').lt(0).Not());

            return image.addBands(lst.rename('LST'))

        return wrap

    # cloudmask for TOA data
    def cloudmasktoa(image):
        qa = image.select('QA_PIXEL')
        mask = qa.bitwiseAnd(1 << 3)
        return image.updateMask(mask.Not())

    # cloudmask for SR data
    def cloudmasksr(image):
        qa = image.select('QA_PIXEL')
        mask = qa.bitwiseAnd(1 << 3) \
            .Or(qa.bitwiseAnd(1 << 4))
        return image.updateMask(mask.Not())

    def LSTcollection(landsat, date_start, date_end, geometry, image_limit, use_ndvi):
        # load TOA Radiance/Reflectance
        collection_dict = ee.Dictionary(COLLECTION.get(landsat))

        landsatTOA = ee.ImageCollection(collection_dict.get('TOA')) \
            .filter(ee.Filter.date(date_start, date_end)) \
            .filterBounds(geometry) \
            .map(cloudmasktoa)

        # load Surface Reflectance collection for NDVI
        landsatSR = ee.ImageCollection(collection_dict.get('SR')) \
            .filter(ee.Filter.date(date_start, date_end)) \
            .filterBounds(geometry) \
            .map(cloudmasksr) \
            .map(NDVIaddBand(landsat)) \
            .map(FVCaddBand(landsat)) \
            .map(NCEP_TPWaddBand) \
            .map(EMaddBand(landsat, use_ndvi))
        # .limit(image_limit,'CLOUD_COVER_LAND') \

        # combine collections
        # all channels from surface reflectance collection
        # except tir channels: from TOA collection
        # select TIR bands
        tir = ee.List(collection_dict.get('TIR'));
        visw = (ee.List(collection_dict.get('VISW'))
                .add('NDVI')
                .add('FVC')
                .add('TPW')
                .add('TPWpos')
                .add('EM')
                )
        landsatALL = (landsatSR.select(visw).combine(landsatTOA.select(tir), True));

        # compute the LST
        landsatLST = landsatALL.map(LSTaddBand(landsat));

        return landsatLST

    def HottestPeriod(FC, start_date, end_date):
        window = 90
        FCcenter = FC.geometry().centroid(1)
        #  CALCULATE DATES OF HOTTEST PERIOD OF HIGH TEMPERATURES FOR EACH PIXEL

        # select dataset, filter by dates and visualize
        dataset = ee.ImageCollection("ECMWF/ERA5/DAILY")
        AirTemperature = (dataset
                          .filter(ee.Filter.And(
            ee.Filter.date(start_date, end_date),
            ee.Filter.bounds(FC)))
                          .select(['maximum_2m_air_temperature'], ['tasmax'])
                          )

        # add date as a band to image collection
        def addDate(image):
            img_date = ee.Date(image.date())
            img_date = ee.Number.parse(img_date.format('YYYYMMdd'))
            return image.addBands(ee.Image(img_date).rename('date').toInt())

        withdates = AirTemperature.map(addDate)

        # create a composite with the hottest day value and dates for every location and add to map
        hottest = withdates.qualityMosaic('tasmax')

        # reduce composite to get the hottest date for centroid of ROI
        resolution = dataset.first().projection().nominalScale()
        NEXtempMax = ee.Number(hottest.reduceRegion(ee.Reducer.firstNonNull(), FCcenter, resolution).get('date'))

        # convert date number to date type
        date = ee.Date.parse('YYYYMMdd', str(NEXtempMax.getInfo()))

        # calculate relative start and end dates
        startwindowadvance = ee.Number(window).multiply(-0.5).add(1)
        endwindowadvance = ee.Number(window).multiply(0.5)

        # calculate 45 days before and after hottest date.  Format as short date.
        startwindowdate = date.advance(startwindowadvance, 'day').format('YYYY-MM-dd')
        endwindowdate = date.advance(endwindowadvance, 'day').format('YYYY-MM-dd')
        return date, startwindowdate, endwindowdate

    def LST(FC, hottestdate, start_date, end_date):
        # select parameters: date range, and landsat satellite
        landsat = 'L8'  # options: 'L4', 'L5', 'L7', 'L8'
        use_ndvi = False
        date_start = start_date  # start for beginning of hottest window or custom date in format '2020-12-20' or start_date for whole achive
        date_end = end_date  # end for end of hottest window or custom date in format '2020-12-20' or end_date for whole achive
        image_limit = 100
        month = hottestdate.get('month')
        month_start = month  # month.subtract(1) # 1 # or month
        month_end = month  # month.add(1) # 12 # or month

        # get landsat collection with added variables: NDVI, FVC, TPW, EM, LST
        LandsatColl = LSTcollection(landsat, date_start, date_end, FC, image_limit, use_ndvi).filter(
            ee.Filter.calendarRange(month_start, month_end, 'month'))

        LSTmean = LandsatColl.select('LST').reduce(ee.Reducer.mean()).subtract(273.15)

        return LSTmean


    # Variables for hottest day search ranges

    # start_date = '2013-03-18'  # start date of Landsat archive to include in hottest day search
    # end_date = '2022-09-17'  # end date of Landsat archive to include in hottest day search
    start_dateYearStr = str(ee.Date(start_date).get('year').getInfo())
    end_dateYearStr = str(ee.Date(end_date).get('year').getInfo())
    
    #boundary_geo = requests.get(boundary_path).json()
    #boundary_geo_ee = geemap.geojson_to_ee(boundary_geo)
    
    # editing by Vinamra to support both local and s3 files
    gdf = gpd.read_file(boundary_path)
    gdf_id = gdf[['geometry']]
    
    boundary_geo_ee = geemap.geopandas_to_ee(gdf_id)

    # obtain LST for location, time and threshold
    hottestdate, start, end = HottestPeriod(boundary_geo_ee, start_date, end_date)

    # obtain LST mean
    LSTmean = LST(boundary_geo_ee, hottestdate, start, end)

    return(LSTmean)


# In[9]:


def extract_ndvi_greenmask(boundary_path, start_date, end_date, NDVIthreshold = 0.4):
    
    '''
    boundary_path: Path to geojson of area of interest
    start_date: Starting date of period for which data is required
    end_date: Ending date of period for which data is required
    NDVIthreshold: Threshold to define healthy gream cover. Default is 0.4
    
    Gives output of both NDVI and green cover
    '''
    
    gdf = gpd.read_file(boundary_path)
    gdf_id = gdf[['geometry']]
    
    FC = geemap.geopandas_to_ee(gdf_id)
     
    NDVIthresholdStr = str(NDVIthreshold)

    s2 = ee.ImageCollection("COPERNICUS/S2")

    def addNDVI(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)

    green = s2.filterDate(startdate, enddate).filterBounds(FC).map(addNDVI)
    green = green.qualityMosaic('NDVI').select('NDVI').float();
    greenScale = green.projection().nominalScale()

    ndvi = green.updateMask(green.select('NDVI'))
    greenmask = ndvi.gte(NDVIthreshold)
    
    # convert to percentages
    greenmask = greenmask.multiply(100)
    
    return ndvi, greenmask


# In[5]:


def export_ee_img_to_drive(img, boundary_path, name, folder, scale):
    
    '''
    img: Image to be exported
    boundary_path: Path to geojson of area of interest
    name: Save name to be given to the file
    folder: folder in google drive where file is to be saved
    scale: Scale/spatial resolution in meters at which file is to be saved. MODIS LST 1000m. Landsat 8 30m.
    '''

    gdf = gpd.read_file(boundary_path)
    fc = ee.FeatureCollection(geemap.geopandas_to_ee(gdf))

    geemap.ee_export_image_to_drive(
            img, 
            description = name,
            folder = folder, 
            scale = scale, 
            region = fc.geometry(),
            maxPixels = 5000000000
        )


# In[6]:


def convert_ee_to_xarray(img, boundary_path, start_date, scale):
    
    '''
    img: Image to be converted
    fc: Feature Collection
    start_date: Starting date of period for which data is required
    scale: Scale/spatial resolution in meters at which file is to be saved. Eg. MODIS LST 1000m, Landsat 8 30m.
    '''
    gdf = gpd.read_file(boundary_path)
    fc = ee.FeatureCollection(geemap.geopandas_to_ee(gdf))

    y,m,d = start_date.split('-')
    img = img.set("system:time_start", ee.Date.fromYMD(int(y), int(m), int(d)).millis())
    
    ds = img.wx.to_xarray(region=fc.geometry(), scale=scale, crs='EPSG:4326')
    ds = ds.squeeze()
    ds = ds.rio.set_spatial_dims(x_dim='x', y_dim='y')
    
    return ds

