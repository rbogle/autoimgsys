# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from flask import Markup
from apscheduler.events import *
from ais.lib.listener import Listener
from ais.ui.models import Event,Job,Plugin
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
    
    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        from flask import request
        #parse get request vars action and plugin
        action = request.args.get('action')
        plugin = request.args.get('plugin')
        
        if plugin is not None:
            plugin = Plugin.query.filtery_by(name=plugin).first()    
        task_logs="Use a widget above to see Task Events"
        
        w=[]
        w.append(self.get_errors_widget(plugin))     
        #w.append(self.get_jobs_widget(plugin))
        #w.append(self.get_events_widget(plugin))
        
        if action == "errors":     
           evts = Event.query.filter_by(code="EVENT_JOB_ERROR").all()
           if len(evts)==0:
               task_logs = "No Error Events Recorded"
           else:
               task_logs = "\n"
               for evt in evts:
                   task_logs += evt.datetime.ctime() +"\t"
                   task_logs += evt.plugin.name +"\t"
                   task_logs += evt.code +"\t\t"
                   task_logs += evt.msg +"\t"
                   task_logs += evt.trace +"\n"
                   
        return self.render(self.view_template, widgets=w, task_logs=task_logs)
    
    def task_error_count(self, plugin=None):
        if plugin is None:
            return Event.query.filter_by(code="EVENT_JOB_ERROR").count()
        return Event.query.filter_by(code="EVENT_JOB_ERROR", plugin=plugin).count()

    def task_run_count(self):
        return len(self.app.scheduler.get_jobs());
               
    def task_success_count(self, plugin=None):
        return Event.query.filter_by(code="EVENT_JOB_EXECUTED", plugin=plugin).count()
    
    def task_errors(self, plugin=None):
        return Event.query.filter_by(code="EVENT_JOB_ERROR", plugin=plugin).all()
    
    def task_events(self, code=None, plugin=None):
        return Event.query.filter_by(code=code, plugin=plugin).all()
        
    def get_errors_widget(self, plugin=None):
        count = self.task_error_count(plugin)
        name = "Task Errors"
        action = Markup( "<a class='btn btn-primary' href='?action=errors'> \
                <span class='glyphicon glyphicon-list'></span> Error Logs</a>") 
        body = "Number of Error Events: <span style='color:"
        if (count):
            body += 'red'
        else:
            body += 'green'
        body += ";'>"+str(count)+"</span>"
        body = Markup(body)
        return (name, body, action)
        
    def get_jobs_widget(self, plugin=None):
        pass
    
    def get_events_widget(self, plugin=None):
        pass