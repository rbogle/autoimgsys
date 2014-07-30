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

from ais.task import Task
from ais.sensors.relay import Relay
from gi.repository import Aravis

import logging
import time
import numpy as np
import cv2
import traceback
import datetime

def Sensor(Object):
    
    def __init__(self, **kwargs):
        self.name = kwargs.get("Name",None)
        self.mac = kwargs.get("Mac", None)
        self.cam = kwargs.get("Cam", None)
        self.dev = kwargs.get("Dev", None)
        self.stream = kwargs.get("Stream", None)
        self.last_payload = 0

def JAI_AD80GE(Task):
    
    def run(self, **kwargs):
    """Initalizes camera system, configures camera, and collects image(s)
        
        Args:
            **kwargs: Named arguments to configure camera for shot(s)
                      Used keywords are the following:
                          
                Datepattern (opt) : passed as strftime format
                                    used for filename YYYY-MM-DDTHHMMSS
                Filename (opt) : Base path and name for filename ./img
                Timeout (opt) : millseconds to wait for image return
                Sequence (opt): list of dictionaries with the following:
                                each dict given will be a numbered image
                ExposureTimeAbs (opt) : image exposure time in uSec
                                        125000 default
                Gain (opt) : 0-26db gain integer steps 0 default
                Height (opt) : requested image height max default
                Width (opt) : requested image width max default
                OffsetX (opt) : requested image x offset 0 default
                OffsetY (opt) : requested image y offest 0 default       
    """
        pass
    
    def respond(self, event):
        pass
    
    def start(self):
        if not self._started: 
            if self._powerctlr is not None:        
                self._power(power_ctl, True)
                time.sleep(self._powerdelay)
            try:
                Aravis.update_device_list()
                for sens in self._sensors
                    sens.cam = Aravis.Camera.new(sens.mac)
                    sens.dev = sens.cam.get_device();
                    sens.stream = sens.cam.create_stream(None, None)
            except TypeError as te:
                #TODO fix me up
                logging.error("Camera could not be instantiated")
                self._started = False                
                return
            
            self._started = True
            
            
    def stop(self):
        self._started = False


    def __init__(self,**kwargs):
        """Initializes camera instance
        
           Args:
               **kwargs Named arguments to configure the camera(s)
                   Sensors: dict of name: mac address for each of the sensors on board
        """
        Task.__init__(self,**kwargs)
        
        sensors = kwargs.get("Sensors",())
        self._sensors = list()
        for s in sensors:
            self._sensors.append( Sensor(**s) )
            
        self._started = False
        self._powerdelay = kwargs.get('Powerdelay', 15)
        self._powerctlr = self._marshal_obj('Powerctlr', **kwargs)
    
        if not isinstance(self._powerctlr, Relay):
            self._powerctlr = None
            logging.error("PowerController is not a Relay Object")
    
    def get_feature_type(self, name, sensor):

        genicam = sensor.dev.get_genicam()
        node = genicam.get_node(name)
        if not node:
            raise AravisException("Feature {} does not seem to exist in camera".format(name))
        return node.get_node_name()
        
    def get_feature_vals(self, name, sensor):
        """
        if feature is an enumeration then return possible values
        """
        ntype = self.get_feature_type(name, sensor)
        if ntype == "Enumeration":
            return sensor.dev.get_available_enumeration_feature_values_as_strings(name)
        else:
            raise AravisException("{} is not an enumeration but a {}".format(name, ntype))
            
    def get_feature(self, name, sensor):
        """
        return value of a feature. independently of its type
        """
        ntype = self.get_feature_type(name, sensor)
        if ntype in ("Enumeration", "String", "StringReg"):
            return sensor.dev.get_string_feature_value(name)
        elif ntype == "Integer":
            return sensor.dev.get_integer_feature_value(name)
        elif ntype == "Float":
            return sensor.dev.get_float_feature_value(name)
        elif ntype == "Boolean":
            return sensor.dev.get_integer_feature_value(name)
        else:
            logging.warning("Feature type not implemented: ", ntype)

    def set_feature(self, name, val. sensor):
        """
        set value of a feature
        """
        ntype = self.get_feature_type(name,sensor)
        if ntype in ( "String", "Enumeration", "StringReg"):
            return sensor.dev.set_string_feature_value(name, val)
        elif ntype == "Integer":
            return sensor.dev.set_integer_feature_value(name, int(val))
        elif ntype == "Float":
            return sensor.dev.set_float_feature_value(name, float(val))
        elif ntype == "Boolean":
            return sensor.dev.set_integer_feature_value(name, int(val))
        else:
            loggomg.warning("Feature type not implemented: ", ntype)  
            
    def _pop_frame(self, sensor):

        buf = sensor.stream.pop_buffer()
        if buf:
            frame = self._array_from_buffer_address(buf)
            sensor.stream.push_buffer(buf)
            return frame
        else:
            return None    
            
    def _create_buffers(self, nb=1, payload=None, sensor):
        if not payload:
            payload = sensor.cam.get_payload()
        logging.info("Creating {} memory buffers of size {}".format(nb, payload))
        for i in range(0, nb):
            sensor.stream.push_buffer(Aravis.Buffer.new_allocate(payload))

    def _array_from_buffer_address(self, buf):
        if not buf:
            return None
        if buf.pixel_format in (Aravis.PIXEL_FORMAT_MONO_8,
                Aravis.PIXEL_FORMAT_BAYER_BG_8):
            INTP = ctypes.POINTER(ctypes.c_uint8)
        else:
            INTP = ctypes.POINTER(ctypes.c_uint16)
        addr = buf.data
        ptr = ctypes.cast(addr, INTP)
        im = np.ctypeslib.as_array(ptr, (buf.height, buf.width))
        im = im.copy()
        return im
    
    def _start_acquisition(self, nb_buffers=1, sensor):
        logging.info("starting acquisition")
        sensor.set_feature("AcquisitionMode", "Continuous") 
        payload = sensor.cam.get_payload()
        if payload != sensor._last_payload:
            #FIXME should clear buffers
            self._create_buffers(nb_buffers, payload, sensor) 
            sensor.last_payload = payload
        sensor.cam.start_acquisition()

    def _stop_acquisition(self, sensor):
        sensor.cam.stop_acquisition()
          
    def _genFilename(self, basename="./img", dtpattern="%Y-%m-%dT%H%M%S"):
        #TODO parse namepattern for timedate pattern?
        #datetime.datetime.now().strftime(dtpattern)
        delim = "_"
        if dtpattern is not None:
            dt = datetime.datetime.now().strftime(dtpattern)
        basename+=delim+dt    
        return basename
    
    def _configShot(self, **kwargs, sensor):
        if self._started:
            self.set_feature("ExposureTimeAbs", kwargs.get("ExposureTimeAbs", 125000),sensor)
            self.set_feature("Gain", kwargs.get("Gain", 0),sensor)
            max_width = self.get_feature("WidthMax",sensor)
            max_height = self.get_feature("HeightMax",sensor)
            #Set ROI
            self.set_feature("Width", kwargs.get("Width", max_width),sensor)
            self.set_feature("Height", kwargs.get("Height", max_height),sensor)
            self.set_feature("OffsetX", kwargs.get("OffsetX", 0),sensor)
            self.set_feature("OffsetY", kwargs.get("OffsetY", 0),sensor)
        else:
            raise(Exception("AVT Camera is not started."))
    
    def _power(self, powerport=0, powerstate=False):
        
        if self._powerctlr is not None:
            try:
                self._powerctlr.set_port(powerport, powerstate)
            except Exception as e:
                logging.error(str(e))                 
        else:        
            logging.error("No power controller is configured.")     