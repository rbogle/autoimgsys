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

import logging
import time
import numpy as np
import cv2
import ctypes
import traceback
import datetime

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
                file_name (opt) : Base path and name for filename ./img
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
        try: # we dont want to crash the ais_service so just log errors
       
           #we need to start camerasys as this is task callback
            powerport= kwargs.get("power_port", 0)
            if not self._started:   
                self.start(power_ctl=powerport)
            
            datepattern = kwargs.get("date_pattern", "%Y-%m-%dT%H%M%S" )    
            filename = self._gen_filename(kwargs.get('file_name', "./img"), 
                                 datepattern)
            imgtype = kwargs.get("image_type", 'tif')
            sequence = kwargs.get('sequence', None)
            pixformats = kwargs.get("pixel_formats", ())
            for pf in pixformats:
                sname = pf.get("sensor", None)                
                self._sensors[sname].cam.set_pixel_format_as_string(pf.get("pixel_format", None))
            #do we have a sequence to take or one-shot
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
    
            self.stop(power_ctl = powerport)        
        except Exception as e:
            logger.error( str(e))
            return 
        logger.info("JAI_AD80GE ran its task")
    
    def respond(self, event):
        pass
    
    def start(self, power_ctl=0):       
        if not self._started: 
            if self._powerctlr is not None:        
                self._power(power_ctl, True)
                time.sleep(self._powerdelay)
            
            self._ar = Aravis()
            for sens in self._sensors.itervalues():
                sens.cam = self._ar.get_camera(sens.mac)
                
            logger.info("JAI_AD80GE is powering up")
            self._started = True       
            
    def stop(self, power_ctl=0):
        if self._started:
            if self._powerctlr is not None:        
                self._power(power_ctl, False)
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
        
        sensors = kwargs.get('sensors',())
        self._sensors = dict()
        for s in sensors :
            name =s.get("name", None)
            self._sensors[name] = Sensor(**s)
            
        self._started = False
        self._powerdelay = kwargs.get('power_delay', 15)
        
        try:
            self._powerctlr = self._marshal_obj('power_ctlr', **kwargs)
            if not isinstance(self._powerctlr, Relay):
                raise TypeError
        except:        
            self._powerctlr = None
            logger.error("PowerController is not a Relay Object")

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
               
    def _gen_filename(self, basename="./img", dtpattern="%Y-%m-%dT%H%M%S"):
        #TODO parse namepattern for timedate pattern?
        #datetime.datetime.now().strftime(dtpattern)
        delim = "_"
        if dtpattern is not None:
            dt = datetime.datetime.now().strftime(dtpattern)
        basename+=delim+dt    
        return basename

            
if __name__ == "__main__":
    
    logger.basicConfig(level=logger.DEBUG)
    
    init_args = {
        "sensors":(
            {"name": "rgb", "mac": "00:0c:df:04:93:93"},
            {"name": "nir", "mac": "00:0c:df:04:a3:93"}        
        )    
    }    
    
    run_args = {
        'pixel_formats':(
            {'sensor':'rgb', 'pixel_format': 'BayerRG8'},
            {'sensor':'nir', 'pixel_format': 'Mono8'}        
        ),
        'file_name': '/home/rbogle/Pictures/jai_tests/hdr',
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
    #jai.add_sensor('RGB','00:0c:df:04:93:93')
    #jai.add_sensor('NIR','00:0c:df:04:a3:93')
        
    
    jai.run(**run_args)
    