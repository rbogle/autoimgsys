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

    The main class is the GigECamera class based on aravis.py
    
"""
from ais.sensors.relay import Relay
import logging
import time
import numpy as np
import cv2
import traceback
import datetime

def GigECamera():
    
