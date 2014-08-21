#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>
""" AVT module provides representations of AVT cameras controlled by vimba

    The main class is the AVT class subclased from ais.Task.
    
"""

from ais.task import Task
from ais.sensors.relay import Relay
import logging
import time
import numpy as np
import cv2
import traceback
import datetime
from pymba import *


class AVT(Task):
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
        try: # we dont want to crash the ais_service so just log errors
           
           #we need to start camerasys as this is task callback
            powerport= kwargs.get("power_port", 0)
            if not self._started:   
                self.start(power_ctl=powerport)
                
            datepattern = kwargs.get("date_pattern", "%Y-%m-%dT%H%M%S" )    
            filename = self._genFilename(kwargs.get('file_name', "./img"), 
                                         datepattern)
            imgtype = kwargs.get("image_type", 'tif')
            timeout = kwargs.get("timeout", 5000)
            sequence = kwargs.get('sequence', None)
            
            #do we have a sequence to take or one-shot
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
                
            self.stop(power_ctl = powerport)        
        except Exception as e:
            logging.error( str(e))
            return
        logging.info("%s ran its task" % self.name)
        
    def respond(self, event):
        pass
    
    def start(self, camera_id=-1, properties={}, power_ctl=0):
        if not self._started: 
            if self._powerctlr is not None:        
                self._power(power_ctl, True)
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
            if properties.get("mode", "RGB") == 'gray':
                self.setProperty("PixelFormat", "Mono8")
            else:
                self.setProperty("PixelFormat", "BayerGB12")
    
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
                self._power(power_ctl, False)
            
            self._started = False    
        

   
    def saveImage(self, name, imgtype="tif", timeout=5000):
        
        data = self._captureFrame(timeout)        
        # Bayer_GB2BGR  used to get acceptable 3-band 16-bit format
        # for cv2.imwrite. this is easiest lib/method to keep 16bit format                             
        bgr = cv2.cvtColor(data, cv2.COLOR_BAYER_GB2BGR)
        #TODO test for file extension first?
        name += "." + imgtype
        cv2.imwrite(name, bgr)           
          
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
        
        Task.__init__(self,**kwargs)
        self._vimba =None
        self._camTable = {}
        self._frame = None
        self._buffer = None # Buffer to store images
        self._properties = {}
        self._camera = None
        self._started = False
        self._powerdelay = kwargs.get('power_delay', 5)
        self._powerctlr = self._marshal_obj('power_ctlr', **kwargs)
        #powcls = self._powerctlr.__class__()
        if not isinstance(self._powerctlr, Relay):
            self._powerctlr = None
            logging.error("PowerController is not a Relay Object")

#
    def __del__(self):
        #This function should disconnect from the Vimba Camera
        if self._camera is not None:

            if self._frame is not None:
                self._frame.revokeFrame()
                self._frame = None

            self._camera.closeCamera()
            
        if self._vimba is not None:
            self._vimba.shutdown()
         
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
                                           dtype = np.uint16,
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
        
    def _genFilename(self, basename="./img", dtpattern="%Y-%m-%dT%H%M%S"):
        #TODO parse namepattern for timedate pattern?
        #datetime.datetime.now().strftime(dtpattern)
        delim = "_"
        if dtpattern is not None:
            dt = datetime.datetime.now().strftime(dtpattern)
        basename+=delim+dt    
        return basename
    
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
    
    def _power(self, powerport=0, powerstate=False):
        
        if self._powerctlr is not None:
            try:
                self._powerctlr.set_port(powerport, powerstate)
            except Exception as e:
                logging.error(str(e))                 
        else:        
            logging.error("No power controller is configured.")
            