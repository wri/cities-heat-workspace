import numpy as np
import netCDF4
from netCDF4 import num2date
import os
import pandas as pd

in_dir = "C:/Users/Administrator/Desktop/capetown/global/raw/"
in_file = 'era5_12_3_6.nc'
out_dir = "C:/Users/Administrator/Desktop/capetown/global/processed/"
out_file = "met_22jan2022.txt"

#load netcdf file
met_f = netCDF4.Dataset(os.path.join(in_dir, in_file))
# print(met_f.dimensions)
# print(met_f.variables)

# open netcdf file. Per ECMWF, unidata netcdf4 module does scaling and offset automatically
with met_f as dataset:
	t2m_var = met_f.variables['t2m']
	u10_var = met_f.variables['u10']
	v10_var = met_f.variables['v10']
	sst_var = met_f.variables['sst']
	cdir_var = met_f.variables['cdir']
	sw_var = met_f.variables['msdrswrfcs']
	lw_var = met_f.variables['msdwlwrfcs']
	d2m_var = met_f.variables['d2m']
	time_var = met_f.variables['time']
	lat_var = met_f.variables['latitude']
	lon_var = met_f.variables['longitude']
# temps go from K to C; global rad (cdir) goes from /hour to /second; wind speed from vectors (pythagorean)
# rh calculated from temp and dew point; vpd calculated from tepm and rh
	times = num2date(time_var[:], units=time_var.units)
	t2m_vals = (t2m_var[:]-273.15)
	d2m_vals = (d2m_var[:]-273.15)
	rh_vals = (100*(np.exp((17.625*d2m_vals)/(243.04+d2m_vals))/np.exp((17.625*t2m_vals)/(243.04+t2m_vals))))
	grad_vals = (cdir_var[:]/3600)
	dir_vals = (sw_var[:])
	dif_vals = (lw_var[:])
	wtemp_vals = (sst_var[:]-273.15)
	wind_vals = (np.sqrt(((np.square(u10_var[:]))+(np.square(v10_var[:])))))
# calc vapor pressure deficit in hPa for future utci conversion. first, get svp in pascals and then get vpd
	svp_vals = (0.61078*np.exp(t2m_vals/(t2m_vals+237.3)*17.2694))
	vpd_vals = ((svp_vals*(1-(rh_vals/100))))*10

#make lat/lon grid
	latitudes = lat_var[:]
	longitudes = lon_var[:]
	latitudes_2d, longitudes_2d = np.meshgrid(latitudes, longitudes, indexing='ij')
	latitudes_flat = latitudes_2d.flatten()
	longitudes_flat = longitudes_2d.flatten()

# create pandas dataframe
df = pd.DataFrame({
	'time':np.repeat(times,len(latitudes_flat)),
	'lat':np.tile(latitudes_flat,len(times)),
	'lon':np.tile(longitudes_flat,len(times)),
	'temp':t2m_vals.flatten(),
	'rh':rh_vals.flatten(),
	'global_rad':grad_vals.flatten(),
	'direct_rad':dir_vals.flatten(),
	'diffuse_rad':dif_vals.flatten(),
	'water_temp':wtemp_vals.flatten(),
	'wind':wind_vals.flatten(),
	'vpd':vpd_vals.flatten()
	})
# round all numbers to two decimal places, which is the precision needed by the model
df = df.round(2)
dfT = df
print(dfT)

# write all to one met file
dfT.to_csv(os.path.join(out_dir, out_file),sep=',',header=True)