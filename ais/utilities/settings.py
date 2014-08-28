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
    'TestCronTrigger': {
        'type': 'cron',
        'module': 'ais.test.test_task',
        'class': 'Test_Task',
        'enable': True,
        'init_args': { 
            'power_ctlr':{
                'module': 'ais.sensors.phidget',
                'class': 'Phidget'
            },
            'power_delay': 5
        },
        'run_args': { 'file_name': 'HDR_test', 'sequence': [
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
            'power_port': 0
            },
        'cron': {'minute': '*/1'}
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
    'TestTaskListener':{
        'module': 'ais.test.test_task',
        'class': 'Test_Task',
        'enable': True,
        'event_mask': EVENT_JOB_EXECUTED
    }
}