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
        enable: whether or not to auto schedule: true, false
        cron: dict of schedule as specd by cron_job in apscheduler
        interval: opts for interval
        date: date for date_job
        init_args: args to be passed to class.__init__()
        callback_args: args to be passed to class.run()
        
'''

tasks = {
    'CronTrigger': {
        'type': 'cron',
        'module': 'ais.cameras.AVT',
        'class': 'AVT',
        'enable': True,
        'init_args': { 
            'Powerctlr':{
                'module': 'ais.sensors.phidget',
                'class': 'Phidget'
            },
            'Powerdelay': 5
        },
        'run_args': { 'Filename': 'HDR_test', 'Sequence': [
                {'ExposureTimeAbs': 125},
                {'ExposureTimeAbs': 250},
                {'ExposureTimeAbs': 500},
                {'ExposureTimeAbs': 1000},
                {'ExposureTimeAbs': 2000},
                {'ExposureTimeAbs': 4000},
                {'ExposureTimeAbs': 8000},
                {'ExposureTimeAbs': 16000},
                {'ExposureTimeAbs': 32000},
                {'ExposureTimeAbs': 64000},
                {'ExposureTimeAbs': 128000},
                {'ExposureTimeAbs': 256000},
                {'ExposureTimeAbs': 512000},
                {'ExposureTimeAbs': 1024000}
            ],
            'Powerport': 0
            },
        'cron': {'minute': '*/10'}
    }
}

'''
    listeners are task subclasses which register with apscheduler to be 
    called when an event triggers.
    Each task is configured by dict with key=name, and members of:
        module: which package/module class belongs to 
        class: which task subclass as should be instantiated
        enable: whether or not to auto register: true, false
        event_mask: the mask passed to indicate which events will apply
        init_args: args to be passed to class.init() as dict
        callback_args: args to be passed to class.respond() as dict
'''

listeners = {
    'ImgPostProc':{
        'module': 'ais.cameras.AVT',
        'class': 'AVT',
        'enable': False,
        'event_mask': EVENT_JOB_EXECUTED
    }
}