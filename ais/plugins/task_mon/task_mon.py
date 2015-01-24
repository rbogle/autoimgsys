# -*- coding: utf-8 -*-

from apscheduler.events import *
from ais.lib.listener import Listener
from ais.ui.models import Event,Job
from ais.ui import db
        
class Task_Monitor(Listener):
    
    def __init__(self, **kwargs):

        super(Task_Monitor, self).__init__(**kwargs)        
        self.viewable = True
        self.widgetized = True
    
    def respond(self, event):
        self.logger.debug("Task_Monitor.Respond called with event: %s" % event) 
        code = msg = tbk = plugin = None
        if isinstance(event, JobExecutionEvent):
            job = Job.query.get(event.job_id)
            if job is not None:
                plugin = job.config.plugin
                
            if event.exception is not None:
                msg = event.exception.message
                tbk = event.traceback
            else:
                msg = str(event.retval)
            for name,num in Listener.event_types.iteritems():
                if event.code==num:
                    code=name
            evt = Event(code=code, datetime=event.scheduled_run_time, plugin=plugin, msg=msg, trace=tbk)
            db.session.add(evt)
            db.session.commit()
        
    def task_error_count(self, plugin=None):
         return Event.query.filter_by(code="EVENT_JOB_ERROR").count()

    def task_success_count(self, plugin=None):
        pass
    def task_errors(self, plugin=None):
        pass
    def task_events(self, code, plugin=None):
        pass