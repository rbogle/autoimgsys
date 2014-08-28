# -*- coding: utf-8 -*-
from ais.task import Task
import logging

class Test_Task(Task):
    
    def run(self, **kwargs):     
        logging.info(self._print_keyword_args("Run called", **kwargs))        
        
    def respond(self, event):
        logging.info("Respond called with event: %s" % event) 
        
    def __init__(self, **kwargs):
        Task.__init__(self,**kwargs)
        logging.info(self._print_keyword_args("Init called", **kwargs)) 
        
    def _print_keyword_args(self, msg, **kwargs):
        # kwargs is a dict of the keyword args passed to the function
        str= msg+'\n'
        for key, value in kwargs.iteritems():
            str+= "%s = %s\n" % (key, value)  
        return str