from plugin import PluginObj
from apscheduler.events import *

class Listener(PluginObj):
    
    event_types = {
        "EVENT_SCHEDULER_START" : EVENT_SCHEDULER_START,
        "EVENT_SCHEDULER_SHUTDOWN" : EVENT_SCHEDULER_SHUTDOWN ,
        "EVENT_EXECUTOR_ADDED" : EVENT_EXECUTOR_ADDED,
        "EVENT_EXECUTOR_REMOVED" : EVENT_EXECUTOR_REMOVED,
        "SEVENT_JOBSTORE_ADDED" : EVENT_JOBSTORE_ADDED,
        "EVENT_JOBSTORE_REMOVED" : EVENT_JOBSTORE_REMOVED,
        "EVENT_ALL_JOBS_REMOVED" : EVENT_ALL_JOBS_REMOVED,
        "EVENT_JOB_ADDED" : EVENT_JOB_ADDED,
        "EVENT_JOB_REMOVED" : EVENT_JOB_REMOVED,
        "EVENT_JOB_MODIFIED" : EVENT_JOB_MODIFIED,
        "EVENT_JOB_EXECUTED" : EVENT_JOB_EXECUTED,
        "EVENT_JOB_ERROR" : EVENT_JOB_ERROR,
        "EVENT_JOB_MISSED" : EVENT_JOB_MISSED    
    }
    
    def __init__(self, **kwargs):
        super(Listener,self).__init__(**kwargs)
        #make listeneres by default enabled then they can decide if they have views
        self.enabled = True

    def respond(self, event):
        """ Called when object registered as an apscheduler event listener
        """
        raise NotImplementedError