# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>
""" aravis module provides representations of aravis gigE cameras controlled by arvais 

    The main class is the GigECamera class subclased from ais.Task.
    
"""

from ais.task import Task
from ais.sensors.relay import Relay
import logging
import time
import numpy as np
import cv2
import traceback
import datetime

def GigECamera(Task):
    
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
    
    def respond(self, event):
        pass