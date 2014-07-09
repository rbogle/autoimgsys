#need logging module for constants
import logging
#need Scheduler for Event_Constants
from apscheduler.events import * 

'''
    logging configuration holds basic overrides for logging.basicConfig
    keys can include:
        format
        filename
        datefmt
        level
'''
log_conf = {

}

'''
    tasks is a dict of task configs to be scheduled with apscheduler
    each task is configured by dict with key=name, and members of:
        type: cron, interval, date
        module: which package/module class belongs to 
        class: which task subclass as should be instantiated
        cron: dict of schedule as specd by cron_job in apscheduler
        interval: opts for interval
        date: date for date_job
        init_args: args to be passed to class.init()
        callback_args: args to be passed to class.run()
        
'''

tasks = {
    'CronTrigger': {
        'type': 'cron',
        'module': 'ais.cameras.AVT',
        'class': 'AVT',
        'init_args': { 'repeat': 10, 'delay': 30},
        'callback_args': { 'mode': 'HDR', 'start': 0, 'step': 2},
        'cron': {'minute': '*/1'}
    }
}

'''
    listeners are task subclasses which register with apscheduler to be called when an event triggers. Each task is configured by dict with key=name, and members of:
        module: which package/module class belongs to 
        class: which task subclass as should be instantiated
        init_args: args to be passed to class.init() as dict
        callback_args: args to be passed to class.run() as dict
'''

listeners = {
    'ImgPostProc':{
        'module': 'ais.cameras.AVT',
        'class': 'AVT',
        'event_mask': EVENT_JOB_EXECUTED
    }
}