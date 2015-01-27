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
    
    @expose('/')
    @expose('/<action>/<plugin>')
    def plugin_view(self, action=None, plugin=None):
        if plugin is not None:
            plugin = Plugin.query.filtery_by(name=plugin).first()
        if action == "task_errors":      
            pass
        elif action == "tasks_running":
            pass
        elif action == "task_success":
            pass
        elif action == "task_events":
            pass
        else:
            pass
        return self.render(self.view_template, widgets=w)
    
    def task_error_count(self, plugin=None):
        return Event.query.filter_by(code="EVENT_JOB_ERROR", plugin=plugin).count()

    def task_run_count(self):
        return len(self.app.scheduler.get_jobs());
               
    def task_success_count(self, plugin=None):
        return Event.query.filter_by(code="EVENT_JOB_EXECUTED", plugin=plugin).count()
    
    def task_errors(self, plugin=None):
        return Event.query.filter_by(code="EVENT_JOB_ERROR", plugin=plugin).all()
    
    def task_events(self, code=None, plugin=None):
        return Event.query.filter_by(code=code, plugin=plugin).all()
        
    def get_errors_widget(self, plugin= None):
        pass
    
    def get_errors_widget(self, plugin= None):
        pass
    
    def get_jobs_widget(self, plugin=None):
        pass
    
    def get_events_widget(self, plugin=None):
        pass