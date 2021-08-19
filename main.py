#!/usr/bin/env python
#
# module load python/GEOSpyD/Ana2019.03_py3.7
#
# Script for 
# 1) read require ment from output
# 2) read times, lats and lons from txt files
# 2) read variables from a nature run sample Netcdf file given lats, lons and times
# 3) write variable with lats, lons and time to Netcdf file
# Usage:  
#

import sys
import os
import yaml
import numpy as np
from netCDF4 import Dataset
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import *
import glob

def get_file_name(ftpl, time) :
  return ftpl.format(y4=time.year, m2=str(time.month).zfill(2), \
                  d2 = str(time.day).zfill(2), h2=str(time.hour).zfill(2), \
                  mn2= str(time.minute).zfill(2), s2=str(time.second).zfill(2))

def get_reference_time_duration(ftpl, start_time):
   last_ = ftpl.rfind('/')
   fpath = ftpl[:last_] if (last_ >=0) else '.'
   fpath = get_file_name(fpath, start_time)

   fname = ftpl[last_+1:]
   wild  = fname.replace('{y4}','*').replace('{m2}','*').replace('{d2}','*').replace('{h2}','*').replace('{mn2}','*')
   files = glob.glob(fpath+'/'+wild)

   assert files, "cannot find files " + fpath+'/'+wild
   k_year = fname.find('{y4}')
   k_mon  = fname.find('{m2}')
   k_day  = fname.find('{d2}') - 2
   k_hour = fname.find('{h2}') - 4
   k_min  = fname.find('{mn2}')- 6
   k_sec  = fname.find('{s2}') - 9
  
   print(files[0]) 
   last_ = files[0].rfind('/')
   fname = files[0][last_+1:]

   YYYY = fname[k_year:k_year+4] if k_year >=0 else '0000'
   MM   = fname[k_mon:k_mon+2] if k_mon >=0 else '00'  
   DD   = fname[k_day:k_day+2] if k_day >=0 else '00' 
   HH   = fname[k_hour:k_hour+2] if k_hour >=0 else '00'
   MN   = fname[k_min:k_min+2]   if k_min >=0 else '00' 
   SS   = fname[k_sec:k_sec+2]   if k_sec >=0 else '00' 
   reftime  = '-'.join((YYYY,MM,DD))+' '+":".join((HH,MN,SS))
   ref_time = datetime.fromisoformat(reftime)
   print("inside: ref_time ", ref_time)
   duration = 0 
   if len(files) >=2 :
      last_ = files[1].rfind('/')
      fname = files[1][last_+1:]
      
      YYYY = fname[k_year:k_year+4] if k_year >=0 else '0000'
      MM   = fname[k_mon:k_mon+2] if k_mon >=0 else '00'  
      DD   = fname[k_day:k_day+2] if k_day >=0 else '00' 
      HH   = fname[k_hour:k_hour+2] if k_hour >=0 else '00'
      MN   = fname[k_min:k_min+2]   if k_min >=0 else '00' 
      SS   = fname[k_sec:k_sec+2]   if k_sec >=0 else '00' 
      reftime1 = '-'.join((YYYY,MM,DD))+' '+":".join((HH,MN,SS))
      ref_time1 = datetime.fromisoformat(reftime1)
      duration = ref_time1 -ref_time
   return ref_time, duration

def read_variables(fname, start_time, var_list, lats, lons):
   # verify time and fname or time stamp in file
   fh = Dataset(fname,mode='r')
   n_level = fh.dimensions['lev'].size    
   n_lat = fh.dimensions['lat'].size
   n_lon = fh.dimensions['lon'].size
   dlat = 180.0/n_lat
   dlon = 360.0/n_lon
  
   Is =((np.array(lats)+90.0 )/dlat).astype('int32')
   Js =((np.array(lons)+180.0)/dlon).astype('int32')
   variables =[]
   for i in range(len(var_list)):
      var_name =  var_list[i]
      var_in = fh.variables[var_name][:, :, :, :]
      var = np.ndarray(shape=(n_level, len(Is)))
      for k in range(len(Is)):
        var[:,k] = var_in[0,:,Is[k],Js[k]]
      variables.append((var_name, n_level, var, fh.variables[var_name].__dict__))
   return variables

def write_variables(fname, start_time, variables, lats, lons, second_increase):

   fh = Dataset(fname, 'w', format='NETCDF4')
   index  = fh.createDimension('index', len(lats))
   level = fh.createDimension('lev', variables[0][1])
   
   second_ = fh.createVariable('second_increase', np.float32, ('index',))
   second_[:] = second_increase[:]
   time_stamp = start_time.strftime('%s-%02d-%02d %02d:%02d:%02d'%(start_time.year, \
                start_time.month,start_time.day,start_time.hour, start_time.minute, start_time.second))
   second_.units = "seconds since " + time_stamp
   second_.long_name = " second_increment" ;
   
   lats_  = fh.createVariable('lat', np.float32, ('index',))
   lats_.long_name = "latitude" ;
   lats_.units = "degrees_north" ;
   lons_  = fh.createVariable('lon', np.float32, ('index',))
   lons_.long_name = "longitude" ;
   lons_.units = "degrees_east" ;

   for i in range(len(variables)) :
      var_name = variables[i][0]
      value_ = fh.createVariable(var_name, np.float32, ('lev','index',))
      value_.setncatts(variables[i][3])
      value_[:,:] = variables[i][2][:,:]
      
   lats_[:] =lats[:]
   lons_[:] =lons[:]

   fh.close()
   
   
if __name__ == '__main__' :
 
   # load input yaml
   stream = open("input.yaml", 'r')
   config = yaml.full_load(stream)

   # driven by output
   start_time = datetime.fromisoformat(str(config['output']['start_time']))
   end_time   = datetime.fromisoformat(str(config['output']['end_time']))
   out_duration = timedelta(seconds = int(config['output']['duration']))
 
   sat_reference_time, sat_duration = get_reference_time_duration(config['locations']['template'], start_time)
   if sat_duration ==0 :
      if 'duration' in config['locations']:
         sat_duration = timedelta(seconds = int(config['locations']['duration'])) 
      else:
         assert false ,  "duration is needed when there is only one file"
   # get the first sat fname
   distance = (start_time - sat_reference_time)/sat_duration
   sat_time = sat_reference_time + int(distance) * sat_duration
   start_sat_fname = get_file_name(config['locations']['template'], sat_time)

   lats = []
   lons = []
   second_increase = []
   last_line = ''
   with open(start_sat_fname, 'rb') as f:
     f.seek(-2, os.SEEK_END)
     while f.read(1) != b'\n':
        f.seek(-2, os.SEEK_CUR)
     last_line = f.readline().decode()
   fin = open(start_sat_fname,'r')
   for _ , line in enumerate(fin):
      data = line.split()
      YY =int(data[0])
      MM =int(data[1])
      DD =int(data[2])
      HH =int(data[3])
      M  =int(data[4])
      SS =int(data[5])
      time  = datetime(YY, MM, DD, HH, M, SS)
      dtime = time - start_time 
      # get to the line
      if (time < start_time):
         continue
      # break if time passes the end time
      if (time  > end_time):
         break
      # start to read fields and write
      if (dtime == out_duration or line == last_line) :

         if (line == last_line) :
            second_increase.append(dtime.total_seconds())
            lats.append(float(str(data[6][0:])))
            lons.append(float(str(data[7][0:])))

         variables = []
         model_fields = config['input_fields']
         # read variables 
         for fields in model_fields :
           for var_names, collection in fields.items():
              ftpl  = config['collections'][collection['collection']]['template']
              model_reference_time, model_frequency = get_reference_time_duration(ftpl, start_time)
              if (model_frequency ==0):
                 if 'duration' in config['collections'][collection['collection']]:
                    model_ferquency = timedelta(seconds = int(config['collections'][collection['collection']]['duration']))
                 else:
                    assert false, "duration is needed in " + collection['collection']
              # by default, find the nearest model file
              distance   = (start_time - model_reference_time)/model_frequency 
              model_time = model_reference_time + int(distance) * model_frequency
              model_fname = get_file_name(config['collections'][collection['collection']]['template'], model_time)
              var_list = var_names.split()
              collection_vars = read_variables(model_fname, model_time, var_list, lats, lons)
              for var in collection_vars:
                 variables.append(var)
         # write out variables
         out_fname = get_file_name(config['output']['template'], start_time)
         write_variables(out_fname, start_time, variables, lats,lons, second_increase)
         variables.clear()
         lats.clear()
         lons.clear()
         second_increase.clear()
         start_time = start_time + out_duration
         dtime = timedelta(seconds = 0)
      
      second_increase.append(dtime.total_seconds())
      lats.append(float(str(data[6][0:])))
      lons.append(float(str(data[7][0:])))
   fin.close()
