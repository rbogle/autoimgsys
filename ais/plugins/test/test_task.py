# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>

from ais.lib.task import Task
import logging, datetime

logger = logging.getLogger(__name__)

class Test_Task(Task):
    
    def run(self, **kwargs):     
        self.last_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')	
                
        logger.info(self._print_keyword_args("Test_Task Run called", **kwargs)) 
              
    def __init__(self, **kwargs):
        Task.__init__(self,**kwargs)
        self.widgetized = True
        self.viewable = True
        logger.info(self._print_keyword_args("Init called", **kwargs)) 
        
    def _print_keyword_args(self, msg, **kwargs):
        # kwargs is a dict of the keyword args passed to the function
        str= msg+'\n'
        for key, value in kwargs.iteritems():
            str+= "%s = %s\n" % (key, value)  
        return str
