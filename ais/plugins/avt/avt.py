#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>

# TODO move the simpleCV source to separate file?

#   several methods and code samples are taken from the VimbaCamera class
#   in the simpleCV python project in the Camera.py module.
#   that code is provided under the BSD software license:
#
#        Copyright (c) 2012, Sight Machine
#        All rights reserved.
#        
#        Redistribution and use in source and binary forms, with or without
#        modification, are permitted provided that the following conditions are met:
#            * Redistributions of source code must retain the above copyright
#              notice, this list of conditions and the following disclaimer.
#            * Redistributions in binary form must reproduce the above copyright
#              notice, this list of conditions and the following disclaimer in the
#              documentation and/or other materials provided with the distribution.
#            * Neither the name of the <organization> nor the
#              names of its contributors may be used to endorse or promote products
#              derived from this software without specific prior written permission.
#        
#        THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#        ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#        WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#        DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
#        DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#        (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#        LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#        ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#        (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#        SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" AVT module provides representations of AVT cameras controlled by vimba

    The main class is the AVT class subclased from ais.Task.
    
"""

from ais.lib.task import PoweredTask
from ais.lib.relay import Relay
import logging
import time
import numpy as np
import cv2
import traceback
import datetime
import os
from pymba import *

logger = logging.getLogger(__name__)

class AVT(PoweredTask):
    """AVT class provides interfaces for control of generic AVT cameras.

        This class relies upon the Vimba SDK and pymba interface for control.
        And implements the Task interface for scheduled runs by ais_service.
        
        Instances of this class used elsewhere will need to at a minimum
        call start() and stop() before and after manipulating the camera 
        properties or capturing images.
        
    """
    def run(self, **kwargs):
        """Initalizes camera system, configures camera, and collects image(s)
            
            Args:
                **kwargs: Named arguments to configure camera for shot(s)
                          Used keywords are the following:
                              
                    date_pattern (opt) : passed as strftime format
                                        used for filename YYYY-MM-DDTHHMMSS
                    file_name (opt) : Base path and name for filename ./img
                    image_type (opt) : Format to save image as. Tiff default
                    timeout (opt) : millseconds to wait for image return
                    sequence (opt): list of dictionaries with the following:
                                    each dict given will be a numbered image
                    ExposureTimeAbs (opt) : image exposure time in uSec
                                            125000 default
                    Gain (opt) : 0-26db gain integer steps 0 default
                    Height (opt) : requested image height max default
                    Width (opt) : requested image width max default
                    OffsetX (opt) : requested image x offset 0 default
                    OffsetY (opt) : requested image y offest 0 default
                    
        """
        try: 
            self.last_run = kwargs
            if not self._started:   
                self.start()
                
            datepattern = kwargs.get("date_pattern", "%Y-%m-%dT%H%M%S" ) 
            split = kwargs.get("date_dir",'Daily')
            nest = kwargs.get("date_dir_nested", False)
            subdir = kwargs.get("sub_dir", None)
            filename = self._gen_filename(kwargs.get('file_prefix', "jai"), 
                                 datepattern,  subdir=subdir, split = split, nest = nest)
            imgtype = kwargs.get("image_type", 'tif')
            timeout = kwargs.get("timeout", 5000)
            sequence = kwargs.get('sequence', None)
            pxfmt = kwargs.get('pixel_format', '')
            if pxfmt not in ('Mono8','BayerGB8'):
                pxfmt = 'BayerGB12'
                self._bit_depth = np.uint16
            else:
                self._bit_depth = np.uint8             
            self.setProperty("PixelFormat", pxfmt)
            #do we have a sequence to take or one-shot
            self.last_run['time'] = datetime.datetime.now().strftime(datepattern)
            if sequence is not None:
                if isinstance(sequence,list):
                    for i,shot in enumerate(sequence):
                        fname=filename+"_"+ "%02d" % i
                        self._configShot(**shot)
                        self.saveImage(fname,imgtype,timeout)
            else:
                #looking for settings for one-shot
                self._configShot(**kwargs)
                self.saveImage(filename,imgtype,timeout)
                
            self.stop()
            
        except Exception as e:
            self.stop()
            logger.error( str(e))
            logger.error( traceback.format_exc())
            self.last_run['success'] = False
            self.last_run['error_msg'] = str(e)
            raise e 
        logger.info("AVT driver ran its task")
        self.last_run['success'] = True  
        
    def configure(self, **kwargs):
        self._powerdelay = kwargs.get('relay_delay', 30)
        self._powerport = kwargs.get('relay_port', 0)
        relay_name = kwargs.get('relay_name', None)        
        if relay_name is not None:
            self._powerctlr = self.manager.getPluginByName(relay_name, 'Relay').plugin_object
        if not isinstance(self._powerctlr, Relay):
            self._powerctlr = None
            logger.error("PowerController is not a Relay Object")          
        self.initalized = True   
        
    def get_configure_properties(self):
        return [
            ('relay_name',"Relay Plugin" ,"Relay Plugin to use for power control."),
            ('relay_delay', "Delay (Sec)", "Number of seconds to wait after enabling Relay."), 
            ('relay_port',"Port Number", "Port on Relay to toggle for control.")
        ]
    def get_run_properties(self):    
        '''
                    date_pattern (opt) : passed as strftime format
                                        used for filename YYYY-MM-DDTHHMMSS
                    file_name (opt) : Base path and name for filename ./img
                    image_type (opt) : Format to save image as. Tiff default
                    timeout (opt) : millseconds to wait for image return
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
            ("timeout","Timeout" ,"Milliseconds to wait for captur.e" ),
            ("sequence","Sequence" , "A set of settings to capture a sequence of images." ), 
            ("exposure_time","Exposure Time","uSec of Exposure. Default: 125000."),
            ("gain","Gain" ,"0-26dB gain, Default: 0." ),
            ("height","Height" ,"Image height, Default: Max." ),
            ("width","Width" ,"Image width, Default: Max." ),
            ("offset_x","OffsetX" ,"Image offset in x pixels. Default 0px." ),
            ("offset_y","OffsetY" ,"Image offset in y pixels. Default 0px." )     
        ]

    def start(self, camera_id=-1, properties={}, power_ctl=0):
        if not self._started: 
            if self._powerctlr is not None:        
                self._power(True)
                logger.info("AVT performing delay for powerup waiting %s sec."%self._powerdelay)
                time.sleep(self._powerdelay)
               
            self._setupVimba()
            
            camlist = self.listAllCameras()
            
            i = 0
            for cam in camlist:
                self._camTable[i] = {'id': cam.cameraIdString}
                i += 1
    
            if not len(camlist):
                raise Exception("Couldn't find any cameras with the Vimba driver.  Use VimbaViewer to confirm you have one connected.")
    
            if camera_id < 9000: #camera was passed as an index reference
                if camera_id == -1:  #accept -1 for "first camera"
                    camera_id = 0
    
                if (camera_id > len(camlist)):
                    raise Exception("Couldn't find camera at index %d." % camera_id)
    
                cam_guid = camlist[camera_id].cameraIdString
            else:
                raise Exception("Index %d is too large" % camera_id)
    
            self._camera = self._vimba.getCamera(cam_guid)
            self._camera.openCamera()
    
            self.uniqueid = cam_guid
    
            self.setProperty("AcquisitionMode","SingleFrame")
            self.setProperty("TriggerSource","Freerun")
    
            # TODO: FIX to get valid modes as prop and adj 
            #       img capture to approp bit depth
            pxfmt = properties.get('pixel_format', '')
            if pxfmt not in ('Mono8','BayerGB8'):
                pxfmt = 'BayerGB12'
                self._bit_depth = np.uint16
            else:
                self._bit_depth = np.uint8
                
            self.setProperty("PixelFormat", pxfmt)
    
            #give some compatablity with other cameras
            if properties.get("mode", ""):
                properties.pop("mode")
    
            if properties.get("height", ""):
                properties["Height"] = properties["height"]
                properties.pop("height")
    
            if properties.get("width", ""):
                properties["Width"] = properties["width"]
                properties.pop("width")
    
            for p in properties:
                self.setProperty(p, properties[p])
              
            self._refreshFrameStats()
            self._started = True

    def stop(self, power_ctl=0):
        if self._started:        
            try:
                if self._camera is not None:
                    if self._frame is not None:
                        self._frame.revokeFrame()
                        self._frame = None
                    self._camera.closeCamera()
                    self._camera = None
                    
                self._vimba.shutdown()
                self._vimba = None
                
            except VimbaException,ve :
                print "Vimba exception %d: %s" % (ve.errorCode, ve.message)
                
            if self._powerctlr is not None:        
                self._power(False)
            
            self._started = False    
        

   
    def saveImage(self, name, imgtype="tif", timeout=5000):
       
        data = self._captureFrame(timeout)        
        # Bayer_GB2BGR  used to get acceptable 3-band 16-bit format
        # for cv2.imwrite. this is easiest lib/method to keep 16bit format 
        pxfmt = self.getProperty("PixelFormat")
        logger.debug("AVT capturing as: %s"%pxfmt)  
        
        if "BayerGB" in pxfmt:                  
            rgb = cv2.cvtColor(data, cv2.COLOR_BAYER_GB2RGB)
        else:
            rgb = data
        #TODO test for file extension first?
        name += "." + imgtype
        logger.debug("AVT capturing and saving image as: %s"%name)
        cv2.imwrite(name, rgb)           
          
    def listAllCameras(self):
        """
        **SUMMARY**
        List all cameras attached to the host

        **RETURNS**
        List of VimbaCamera objects, otherwise empty list
        VimbaCamera objects are defined in the pymba module
        """
        if not self._started:
            cameraIds = self._vimba.getCameraIds()
            ar = []
            for cameraId in cameraIds:
                ar.append(self._vimba.getCamera(cameraId))
            return ar
        else:
            raise (VimbaException(-5))
            
    def getProperty(self, name):
        """
        **SUMMARY**
        This retrieves the value of the Vimba Camera attribute

        There are around 140 properties for the Vimba Camera, so reference the
        Vimba Camera pdf that is provided with
        the SDK for detailed information

        Throws VimbaException if property is not found or not implemented yet.

        """        
        return self._camera.__getattr__(name)
        
    def setProperty(self, name, value, skip_buffer_size_check=False):
        """
        **SUMMARY**
        This sets the value of the Vimba Camera attribute.

        There are around 140 properties for the Vimba Camera, so reference the
        Vimba Camera pdf that is provided with
        the SDK for detailed information

        Throws VimbaException if property not found or not yet implemented

        """
        ret = self._camera.__setattr__(name, value)

        #just to be safe, re-cache the camera metadata
        if not skip_buffer_size_check:
            self._refreshFrameStats()

        return ret
    
    def runCommand(self,command):
        """
        **SUMMARY**
        Runs a Vimba Command on the camera

        Valid Commands include:
        * AcquisitionAbort
        * AcquisitionStart
        * AcquisitionStop

        **RETURNS**

        0 on success
        """
        return self._camera.runFeatureCommand(command)
 
    def __init__(self, **kwargs):
        
        super(AVT,self).__init__(**kwargs)
        self._vimba =None
        self._camTable = {}
        self._frame = None
        self._buffer = None # Buffer to store images
        self._properties = {}
        self._camera = None
        self._started = False
        self._powerdelay = kwargs.get('relay_delay', 30)
        #self._powerctlr = self._marshal_obj('power_ctlr', **kwargs)
        self._powerport = kwargs.get('relay_port', 0)
        self._bit_depth = np.uint16
        #powcls = self._powerctlr.__class__()
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

#    This may be causing problems for garbage collection 
#    def __del__(self):
#        #This function should disconnect from the Vimba Camera
#        if self._camera is not None:
#
#            if self._frame is not None:
#                self._frame.revokeFrame()
#                self._frame = None
#
#            self._camera.closeCamera()
#                        
#            
#        if self._vimba is not None:
#            self._vimba.shutdown()
         
    def _refreshFrameStats(self):
        self.width = self.getProperty("Width")
        self.height = self.getProperty("Height")
        self.pixelformat = self.getProperty("PixelFormat")

    def _getFrame(self):
        if not self._frame:
            self._frame = self._camera.getFrame()    # creates a frame
            self._frame.announceFrame()

        return self._frame        
            
    #returns numpy array 16-bit frame data in PixelMode format
    def _captureFrame(self, timeout = 5000):
        
        try:
            c = self._camera
            f = self._getFrame()

            c.startCapture()
            f.queueFrameCapture()
            c.runFeatureCommand('AcquisitionStart')
            c.runFeatureCommand('AcquisitionStop')
            try:
                f.waitFrameCapture(timeout)
            except Exception, e:
                print "Exception waiting for frame: %s: %s" % (e, traceback.format_exc())
                raise(e)

            imgData = f.getBufferIntData()
            moreUsefulImgData = np.ndarray(buffer = imgData,
                                           dtype = self._bit_depth,
                                           shape = (f.height, f.width, 1))
            c.endCapture()
            return moreUsefulImgData
        except VimbaException, ve:
            print "VimbaException %d: %s" % (ve.errorCode, e.message)
            raise(ve)
        except Exception, e:
            print "Exception acquiring frame: %s: %s" % (e, traceback.format_exc())
            raise(e)
 
    def _setupVimba(self):
        
        self._vimba = Vimba()
        self._vimba.startup()
        system = self._vimba.getSystem()
        if system.GeVTLIsPresent:
            system.runFeatureCommand("GeVDiscoveryAllOnce")
            time.sleep(0.2)           
        
    def _gen_filename(self, prefix="avt", dtpattern="%Y-%m-%dT%H%M%S", subdir=None, split=None, nest=False):

        now = datetime.datetime.now()
        delim = "_"
        #set root path to images
        if self.filestore is None:
            imgpath = "/tmp/avt"
        else:
            imgpath = self.filestore
        #tack on subdir to imgpath if requested    
        if subdir is not None:
            imgpath+=subdir
        #try to make imagepath    
        if not os.path.isdir(imgpath):    
            try:
                os.makedirs(imgpath)
            except OSError:
                if not os.path.isdir(imgpath):
                    logger.error("AVT cannot create directory structure for image storage")    
        #if asked to make more subdirs by date do it:            
        if split is not None:
            imgpath = self._split_dir(now,imgpath,split,nest)
        #make datepattern for file name if asked for
        if dtpattern is not None:
            dt = now.strftime(dtpattern)
        #we return the path and name prefix with dt stamp
        #save_image adds sensor and sequence number and suffix.
        return imgpath+"/"+prefix+delim+dt

    def _split_dir(self, atime, root="/tmp/avt",freq="Daily", nested=False):
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
                    logger.error("AVT cannot create directory structure for image storage")
        return root
    
    def _configShot(self, **kwargs):
        if self._started:
            self.setProperty("ExposureTimeAbs", kwargs.get("exposure_time", 125000))
            self.setProperty("Gain", kwargs.get("gain", 0))
            max_width = self.getProperty("WidthMax")
            max_height = self.getProperty("HeightMax")
            #Set ROI
            self.setProperty("Width", kwargs.get("width", max_width))
            self.setProperty("Height", kwargs.get("height", max_height))
            self.setProperty("OffsetX", kwargs.get("offset_x", 0))
            self.setProperty("OffsetY", kwargs.get("offset_y", 0))
        else:
            raise(Exception("AVT Camera is not started."))
    
if __name__ == "__main__":
    
    logging.basicConfig(level=logging.DEBUG)
    
    init_args ={
        "power_ctlr":{
            'class': "Phidget",
            'module': 'ais.plugins.phidget.phidget'
        },
        'relay_delay': 30,
        'relay_port':0,
        
    }   
    
    run_args = {

        'file_prefix': 'hdr',
        'sub_dir' : "/test",
        'date_dir' : "Daily",
        'date_dir_nested': False,
        'pixel_format': 'BayerGB8',
        'sequence':[
            {'exposure_time': 977},
            {'exposure_time': 1953},
            {'exposure_time': 3906},
            {'exposure_time': 7813},
            {'exposure_time': 15625},
            {'exposure_time': 31250},
            {'exposure_time': 62500},
            {'exposure_time': 125000},
            {'exposure_time': 250000},
            {'exposure_time': 500000},
            {'exposure_time': 1000000}
        ]
    }    
    
    cam = AVT(**init_args)        
    
    cam.run(**run_args)
            