# -*- coding: utf-8 -*-

from apscheduler.events import *
from ais.lib.listener import Listener
        
class Task_Monitor(Listener):
    
    def __init__(self, **kwargs):

        super(Task_Monitor, self).__init__(**kwargs)        
        self.viewable = True
        self.widgetized = True
    
    def respond(self, event):
        self.logger.debug("Task_Monitor.Respond called with event: %s" % event) 
        if isinstance(event, JobExecutionEvent):
            self.logger.info("Job Id: %s ran at %s" %(event.job_id, event.scheduled_run_time))

        
