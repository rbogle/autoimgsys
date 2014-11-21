# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>
""" JAI module provides representations of JAI gigE cameras controlled by arvais 

    The first class is the JAI_AD80GE class subclased from ais.Task
    This device has two cameras one RGB visible and one Mono NIR.
"""    

from ais.plugins.jai.aravis import *
from ais.lib.task import PoweredTask
from ais.lib.relay import Relay
import pprint
import logging
import time
import numpy as np
import cv2
import ctypes
import traceback
import datetime
import os

logger = logging.getLogger(__name__)

class Sensor(object):
    
    def __init__(self, **kwargs):
        self.name = kwargs.get("name",None)
        self.mac = kwargs.get("mac", None)
        self.cam = None

class JAI_AD80GE(PoweredTask):
    
    def run(self, **kwargs):
        """Initalizes camera system, configures camera, and collects image(s)
        
        Args:
            **kwargs: Named arguments to configure camera for shot(s)
                      Used keywords are the following:
                          
                date_pattern (opt) : passed as strftime format
                                    used for filename YYYY-MM-DDTHHMMSS
                file_prefix (opt) : Prefix for filename 'jai'
                sub_dir (None, hourly, daily, monthly, yearly) : make subdirs for storage
                sub_dir_nested (opt): make a separate nested subdir for each y,m,d,h or single subdir as yyyy_mm_dd_hh
                timeout (opt) : millseconds to wait for image return
                sequence (opt): list of dictionaries with the following:
                                each dict given will be a numbered image
                exposure_time (opt) : image exposure time in uSec
                                        33319 (1/30th) default
                                        20 is min
                gain (opt) : 0-26db gain integer steps 0 default
                height (opt) : requested image height max default
                width (opt) : requested image width max default
                offset_x (opt) : requested image x offset 0 default
                offset_y (opt) : requested image y offest 0 default       
        """
        self.last_run = kwargs
        try: # we dont want to crash the ais_service so just log errors
       
           #we need to start camerasys as this is task callback
            if not self._started:   
                self.start()
            
            datepattern = kwargs.get("date_pattern", "%Y-%m-%dT%H%M%S" ) 
            split = kwargs.get("sub_dir",'Daily')
            nest = kwargs.get("sub_dir_nested", False)
            filename = self._gen_filename(kwargs.get('file_prefix', "jai"), 
                                 datepattern, split = split, nest = nest)
            imgtype = kwargs.get("image_type", 'tif')
            sequence = kwargs.get('sequence', None)
            pixformats = kwargs.get("pixel_formats", ())
            for pf in pixformats:
                sname = pf.get("sensor", None)                
                self._sensors[sname].cam.set_pixel_format_as_string(pf.get("pixel_format", None))
            #do we have a sequence to take or one-shot
            self.last_run['time'] = datetime.datetime.now().strftime(datepattern)
            if sequence is not None:
                if isinstance(sequence,list):
                    for i,shot in enumerate(sequence):
                        fname=filename+"_"+ "%02d" % i
                        self.configure_shot(**shot)
                        self.save_image(fname,imgtype)
            else:
                #looking for settings for one-shot
                self.configure_shot(**kwargs)
                self.save_image(filename,imgtype)
            self.stop()        
        except Exception as e:
            self.stop()
            logger.error( str(e))
            logger.error( traceback.format_exc())
            self.last_run['success'] = False
            self.last_run['error_msg'] = str(e)
            raise e 
        logger.info("JAI_AD80GE ran its task")
        self.last_run['success'] = True     
        
    def status(self):
        status= {}
        try:
            if not self._started:   
                self.start()
            for sensor in self._sensors.itervalues():
                sensor_status = {}
                sensor_status['Name'] = sensor.name
                sensor_status['Mac'] = sensor.mac
                sensor_status["Camera model"] = sensor.cam.get_model_name()
                (x,y,w,h) = sensor.cam.get_region()
                sensor_status["Image size"]= "(%s,%s)" %(w,h)
                sensor_status["Image offset"] = "(%s,%s)" %(x,y)
                sensor_status["Sensor size"]=sensor.cam.get_sensor_size()
                sensor_status["Exposure"]=sensor.cam.get_exposure_time()
                sensor_status["Frame rate"]=sensor.cam.get_frame_rate()
                sensor_status["Payload"]=sensor.cam.get_payload()
                sensor_status["AcquisitionMode"]=sensor.cam.get_string_feature("AcquisitionMode")
                sensor_status["TriggerSource"]=sensor.cam.get_string_feature("TriggerSource")
                sensor_status["TriggerMode"]=sensor.cam.get_string_feature("TriggerMode")
                sensor_status["Bandwidth"]=sensor.cam.get_integer_feature("StreamBytesPerSecond")
                sensor_status["PixelFormat"]=sensor.cam.get_string_feature("PixelFormat")
                sensor_status["ExposureAuto"]=sensor.cam.get_string_feature("ExposureAuto")
                sensor_status["PacketSize"]=sensor.cam.get_integer_feature("GevSCPSPacketSize")

                ipnum=sensor.cam.get_integer_feature("GevCurrentIPAddress")
                o1 = int(ipnum / 16777216) % 256
                o2 = int(ipnum / 65536) % 256
                o3 = int(ipnum / 256) % 256
                o4 = int(ipnum) % 256
                sensor_status["Current IP Addr"]='%(o1)s.%(o2)s.%(o3)s.%(o4)s' % locals()
                status[sensor.name] = sensor_status
                
            self.stop()
            
        except Exception as e:
            self.stop()
            logger.error( str(e))
            logger.error( traceback.format_exc())
            return None
            
        return status
        
    def configure(self, **kwargs):
        logger.info("Configuration called")
        sensors = kwargs.get('sensors',None)
        if sensors is not None:
            self._sensors = dict()
            logger.info("Setting sensors for JAI camera")
            for s in sensors :
                
                name =s.get("name", None)
                self._sensors[name] = Sensor(**s)
                logger.info("Sensor: %s loaded" %name)
            self.initalized = True 
            
        self._powerdelay = kwargs.get('relay_delay', 15)
        self._powerport = kwargs.get('relay_port', 0)
        relay_name = kwargs.get('relay_name', None)  
        self._powerctlr = None
        if relay_name is not None:
            #TODO what if we're not running under the ais_service?
            self._powerctlr = self.manager.getPluginByName(relay_name, 'Relay').plugin_object
            if self._powerctlr is not None:
                logger.info("JAI power controller set to use: %s on port %s with delay %s" 
                    %(relay_name, self._powerport, self._powerdelay))
            else:
                logger.error("JAI power controller is not set!")
        if not isinstance(self._powerctlr, Relay):
            logger.error("Plugin %s is not available" %relay_name)          
  
        
    def get_configure_properties(self):
        return [
            ('sensors',"Sensor List" ,"List with {name=sensorname, mac=###}"),
            ('relay_name',"Relay Plugin" ,"Relay Plugin to use for power control."),
            ('relay_delay', "Delay (Sec)", "Number of seconds to wait after enabling Relay."), 
            ('relay_port',"Port Number", "Port on Relay to toggle for control.")
        ]
    def get_run_properties(self):    
        '''
                    date_pattern (opt) : passed as strftime format
                                        used for filename YYYY-MM-DDTHHMMSS
                    file_prefix (opt) : Base path and name for filename ./img
                    image_type (opt) : Format to save image as. Tiff default
                    pixelformats (opt) : list of image format to capture for each sensor
                    sequence (opt): list of dictionaries with the following:
                                    each dict given will be a numbered image
                    ExposureTimeAbs (opt) : image exposure time in uSec
                                            125000 default
                    Gain (opt) : 0-26db gain integer steps 0 default
                    Height (opt) : requested image height max default
                    Width (opt) : requested image width max default
                    OffsetX (opt) : requested image x offset 0 default
                    OffsetY (opt) : requested image y offest 0 default
        '''
        return [
            ("date_pattern","Date Format","Used in filenaming, Default is YYYY-MM-DDTHHMMSS."),
            ("file_name","File Location", "Base Path and prefix for filenaming. Default: /tmp/img_."),
            ("image_type","Image Format" ,"Image format to save as. Default: tif." ),
            ("pixel_formats","Pixel Formats" ,"List of image formats for each sensor: { name=sensor, pixel_format=format}" ),
            ("sequence","Sequence" , "A set of settings to capture a sequence of images." ), 
            ("exposure_time","Exposure Time","uSec of Exposure. Default: 125000."),
            ("gain","Gain" ,"0-26dB gain, Default: 0." ),
            ("height","Height" ,"Image height, Default: Max." ),
            ("width","Width" ,"Image width, Default: Max." ),
            ("offset_x","OffsetX" ,"Image offset in x pixels. Default 0px." ),
            ("offset_y","OffsetY" ,"Image offset in y pixels. Default 0px." )     
        ]
   
    def start(self):       
        if not self._started: 
            logger.info("JAI_AD80GE is powering up")
            if self._powerctlr is not None:        
                self._power(True)
                logger.debug("Power delay for %s seconds" %self._powerdelay)
                time.sleep(self._powerdelay)
                logger.debug("Power delay complete, connecting to camera")
            self._ar = Aravis()
            for sens in self._sensors.itervalues():
                sens.cam = self._ar.get_camera(sens.mac) 
            logger.info("JAI_AD80GE started")
            self._started = True       
            
    def stop(self):
        if self._powerctlr is not None:        
            self._power( False)
            logger.info("JAI_AD80GE is powering down")        
        self._started = False 
            
    def save_image(self, name, imgtype=".tif"):
        if not self._started:
            logger.error("Camera device must be started before capture")
            return None
        else:
            for sens in self._sensors.itervalues():
                sens.cam.create_buffers(1)
                data = self._capture_frame(sens)
                pxf = sens.cam.get_pixel_format_as_string()
                #convert bayer data
                #TODO: handle packed formats?
                if 'BayerRG' in pxf: #JAI_AD80GE outputs only RG pattern.
                    data = cv2.cvtColor(data, cv2.COLOR_BAYER_RG2RGB)
                    # Bayer_RG2RGB  used to get acceptable RGB format
                # for cv2.imwrite. this is easiest lib/method to keep 16bit format                             
                #TODO test name for file extension first?
                #TODO add metadata?
                iname = name+ "_"+sens.name+"." + imgtype
                logger.debug("Jai capturing and saving image as: %s"%iname)
                cv2.imwrite(iname, data)
    
    def configure_sensor(self,sensor, **kwargs ):
        if self._started:
              camconf = kwargs.get("sensor_config", {}) 
              for setting in camconf:
                  stype = setting.get("type", None)
                  sname = setting.get("name", None)
                  sval = setting.get("value", None)
                  if(stype == "string"):
                      sensor.cam.set_string_feature(sname, sval)
                  elif(stype=="integer"):
                      sensor.cam.set_integer_feature(sname, sval)
                  elif(stype=="float"):    
                      sensor.cam.set_float_feature(sname, sval)
        else:
            logger.error("JAI_AD80GE is not started")
            raise Exception("JAI Camera is not started.")
        
    def configure_shot(self, **kwargs):
        if self._started:
            for sensor in self._sensors.itervalues():
                sensor.cam.set_exposure_time(kwargs.get("exposure_time", 33319))
                sensor.cam.set_gain(kwargs.get("gain", 0))
                max_width,max_height  = sensor.cam.get_sensor_size()
                #Set ROI
                sensor.cam.set_region(kwargs.get("offset_x", 0),
                                      kwargs.get("offset_y", 0),                                      
                                      kwargs.get("width", max_width),
                                      kwargs.get("weight", max_height))
        else:
            logger.error("JAI_AD80GE is not started")
            raise Exception("JAI Camera is not started.")
       
    def add_sensor(self, name, macaddress):
        kwa = {'name': name, 'mac': macaddress}
        sensor = Sensor(**kwa)
        self._sensors[name] = sensor       

    def __init__(self,**kwargs):
        """Initializes camera instance
        
           Args:
               **kwargs Named arguments to configure the camera(s)
                   Sensors: dict of name: mac address for each of the sensors on board
        """
        super(JAI_AD80GE,self).__init__(**kwargs)
        
        sensors = kwargs.get('sensors', None)
        self._sensors = dict()
        self.last_run = None
        
        if sensors is not None:
            for s in sensors :
                name =s.get("name", None)
                self._sensors[name] = Sensor(**s)
            self.initalized = True
                      
        self._started = False
        self._powerdelay = kwargs.get('relay_delay', 30)
        self._powerport = kwargs.get('relay_port', 0)
        if 'power_ctlr' in kwargs:
            try:
                self._powerctlr = self._marshal_obj('power_ctlr', **kwargs)
                if not isinstance(self._powerctlr, Relay):
                    raise TypeError
            except:        
                self._powerctlr = None
                logger.error("Could not marshall Relay Object")
        elif 'relay_name' in kwargs:
            relay_name = kwargs.get('relay_name', None)
            try:
                self._powerctlr = self.manager.getPluginByName(relay_name, 'Relay').plugin_object
                if not isinstance(self._powerctlr, Relay):
                    self._powerctlr = None
                    logger.error("Plugin %s is not a Relay Object" %relay_name)   
            except:
                logger.error("Plugin %s is not available" %relay_name)
                    
    def _capture_frame(self, sensor):
        frame = None
        if sensor is not None:
            sensor.cam.start_acquisition_continuous() 
            frame = sensor.cam.get_frame()
            sensor.cam.stop_acquisition()
        else:
            logger.error("Capture_Frame failed not a valid sensor")
            raise Exception ("Invalid Sensor Object")
        return frame 
               
    def _gen_filename(self, prefix="jai", dtpattern="%Y-%m-%dT%H%M%S", split=None, nest=False):
        #TODO parse namepattern for timedate pattern?
        #datetime.datetime.now().strftime(dtpattern)
        now = datetime.datetime.now()
        delim = "_"
        if self.filestore is None:
            imgpath = "/tmp/jai"
        else:
            imgpath = self.filestore
            
        if not os.path.isdir(imgpath):    
            try:
                os.makedirs(imgpath)
            except OSError:
                if not os.path.isdir(imgpath):
                    logger.error("Jai cannot create directory structure for image storage")    
                    
        if split is not None:
            imgpath = self._split_dir(now,imgpath,split,nest)
        if dtpattern is not None:
            dt = now.strftime(dtpattern)
        #we return the path and name prefix with dt stamp
        #save_image adds sensor and sequence number and suffix.
        return imgpath+"/"+prefix+delim+dt

    def _split_dir(self, atime, root="/tmp/jai",freq="Daily", nested=False):
        '''
            _split_dir will make a directory structure based on a datetime object
            , frequency, and whether or not it should be nested. 
        '''
        if nested:
            delim="/"
        else:
            delim ="_"
        if freq in ['year', 'Year', 'yearly', 'Yearly']: 
            root+='/'+ str(atime.year)
        elif freq in ['month', 'Month', 'Monthly', 'monthly']:
            root+='/'+str(atime.year)+delim+"%02d"%atime.month    
        elif freq in ['day', 'daily', 'Day', 'Daily']:
            root+='/'+str(atime.year)+delim+"%02d"%atime.month+delim+"%02d"%atime.day  
        elif freq in ['hour', 'hourly', 'Hour', 'Hourly']:
            root+='/'+str(atime.year)+delim+"%02d"%atime.month+delim+"%02d"%atime.day+delim+"%02d"%atime.hour
        if not os.path.isdir(root):    
            try:
                os.makedirs(root)
            except OSError:
                if not os.path.isdir(root):
                    logger.error("Jai cannot create directory structure for image storage")
        return root
            
if __name__ == "__main__":
    
    logging.basicConfig(level=logging.DEBUG)
    
    init_args = {
        "sensors":(
            {"name": "rgb", "mac": "00:0c:df:04:93:94"},
            {"name": "nir", "mac": "00:0c:df:04:a3:94"}        
        ),
        "power_ctlr":{
            'class': "Phidget",
            'module': 'ais.plugins.phidget.phidget'
        },
        'relay_delay': 30,
        'relay_port':0
    }    
    
    run_args = {
        'pixel_formats':(
            {'sensor':'rgb', 'pixel_format': 'BayerRG8'},
            {'sensor':'nir', 'pixel_format': 'Mono8'}        
        ),
        'file_prefix': 'hdr',
        'sequence':[
            {'exposure_time': 20},
            {'exposure_time': 40},
            {'exposure_time': 120},
            {'exposure_time': 240},
            {'exposure_time': 480},
            {'exposure_time': 960},
            {'exposure_time': 1920},
            {'exposure_time': 3840},
            {'exposure_time': 7680},
            {'exposure_time': 15360},
            {'exposure_time': 30720},
        ]
    }    
    
    jai = JAI_AD80GE(**init_args)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(jai.status())
    #jai.run(**run_args)
    