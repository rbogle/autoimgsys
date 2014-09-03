# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>

from ais.task import Task
import logging

class Test_Task(Task):
    
    def run(self, **kwargs):     
        logging.info(self._print_keyword_args("Test_Task Run called", **kwargs))        
        
    def respond(self, event):
        logging.info("Test_Task Respond called with event: %s" % event) 
        
    def __init__(self, **kwargs):
        Task.__init__(self,**kwargs)
        logging.info(self._print_keyword_args("Init called", **kwargs)) 
        
    def _print_keyword_args(self, msg, **kwargs):
        # kwargs is a dict of the keyword args passed to the function
        str= msg+'\n'
        for key, value in kwargs.iteritems():
            str+= "%s = %s\n" % (key, value)  
        return str