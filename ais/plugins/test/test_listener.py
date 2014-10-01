# -*- coding: utf-8 -*-

from apscheduler.events import *
from ais.lib.listener import Listener
import logging

logger = logging.getLogger(__name__)
        
class Test_Listener(Listener):
    
    def respond(self, event):
        logger.info("Test_Listener.Respond called with event: %s" % event) 
        if isinstance(event, JobExecutionEvent):
            logger.info("Job Id: %s ran at %s" %(event.job_id, event.scheduled_run_time))

        
