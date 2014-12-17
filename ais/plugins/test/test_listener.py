# -*- coding: utf-8 -*-

from apscheduler.events import *
from ais.lib.listener import Listener
        
class Test_Listener(Listener):
    
    def respond(self, event):
        self.logger.info("Test_Listener.Respond called with event: %s" % event) 
        if isinstance(event, JobExecutionEvent):
            self.logger.info("Job Id: %s ran at %s" %(event.job_id, event.scheduled_run_time))

        
