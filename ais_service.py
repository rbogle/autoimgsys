#!/usr/bin/python

#temp imports
from pprint import pprint #for debuggin
import time #for while loop sleep
import os.path
import argparse

#main imports
import logging
import importlib
import ais.utilities.settings as settings
from ais.task import Task
from apscheduler.schedulers.background import BackgroundScheduler

def configure_logging(config):

    log_file_name = config.get('filename', '')
    log_level = config.get('level', logging.DEBUG)
    log_date_fmt = config.get('datefmt', '')
    log_format = config.get('format', 
                    '%(asctime)s %(module)s - %(levelname)s: %(message)s')    
    logging.basicConfig(filename=log_file_name, level=log_level,
                        datefmt=log_date_fmt, format=log_format)

def martial_task(name, task, tasklist):

    init_args = task.get('init_args', {});
    # instantiate class 
    try:
       task_mod= importlib.import_module(task.get('module'))
       task_cls = getattr(task_mod, task.get('class'))
       task_obj = task_cls(**init_args)
       #check that we have Task object
       assert(issubclass(task_cls,Task))
    except AssertionError:
        logging.error("Specified class %s is not a Task" % task.get('class'))
        return
    except Exception as e:   
        logging.error("error: %s" % type(e))
        logging.error("Could not build class %s" % task.get('class'))
        return 
     #push to tasklist with key=name, val modified task+obj   
    task['obj'] = task_obj
    tasklist[name] = task    
    logging.info("Task %s martialed and configured" % name)
 
def martial_listener(name, task, listeners):

    init_args = task.get('init_args', {});
    # instantiate class 
    try:
       task_mod= importlib.import_module(task.get('module'))
       task_cls = getattr(task_mod, task.get('class'))
       task_obj = task_cls(**init_args)
       #check that we have Task object
       assert(issubclass(task_cls,Task))
    except AssertionError:
        logging.error("Specified class %s is not a Task" % task.get('class'))
        return
    except Exception as e:   
        logging.error("error: %s" % type(e))
        logging.error("Could not build class %s" % task.get('class'))
        return 
    #push to listeners with key=name, val modified task+obj   
    task['obj'] = task_obj
    listeners[name] = task    
    logging.info("Listener %s martialed and configured" % name)    
    
def schedule_tasks(scheduler, tasklist):
    
    for tname,task in tasklist.iteritems():
        if task.get('enable', True):
            task_type = task['type']
            task_obj = task['obj']
            call_args = task.get('run_args', None)
            my_trigger_args = None
            my_trigger = ""
            if task_type=='cron' or task_type=='interval' or task_type=='date':
                my_trigger=task_type
                my_trigger_args = task.get(task_type, None)
                if my_trigger_args is not None:
                    scheduler.add_job(task_obj.run, trigger=my_trigger, 
                              kwargs = call_args, id=tname, 
                              name=tname, replace_existing=True, **my_trigger_args)                        
                    logging.info("Task %s scheduled" % tname)
                else:
                    logging.error("Task arguments invalid")
                    continue
            else:
                logging.error("Invalid trigger type for scheduled job")
                continue  
        else:
            logging.info("Task $s not enabled" % tname)
#                if 'cron' in task:
#
##                    scheduler.add_cron_job( task_obj.run, 
##                                    year=task['cron'].get('year',None),
##                                    month=task['cron'].get('month',None),
##                                    day=task['cron'].get('day',None),
##                                    week=task['cron'].get('week',None),
##                                    day_of_week=task['cron'].get('dow',None),
##                                    hour=task['cron'].get('hour',None),
##                                    minute=task['cron'].get('minute',None),
##                                    second=task['cron'].get('second',None),
##                                    start_date = task['cron'].get('startdate',None),
##                                    kwargs = call_args,
##                                    name=tname)
#                else:
#                    logging.error("Cron task %s has no cron specified" % tname)
#                    
#            elif type=='date':
#                if 'date' in task:
##                    scheduler.add_date_job( task_obj.run, date=task['date'],
##                                    kwargs=call_args,
##                                    name=tname)
#                else:
#                    logging.error("Date task %s has no date specified" % tname)
#                    
#            elif type=='interval':
#                if 'interval' in task:
##                    scheduler.add_interval_job( task_obj.run, 
##                                    days=task['interval'].get('days',0),
##                                    weeks=task['interval'].get('weeks',0),
##                                    hours=task['interval'].get('hours',0),
##                                    minutes=task['interval'].get('minutes',0),
##                                    seconds=task['interval'].get('seconds',0),
##                                    start_date = task['interval'].get('startdate',None),
##                                    kwargs = call_args,
##                                    name=tname)
#                else:
#                    logging.error("Interval task %s has no interval specified" 
#                                    % tname)
                   

            
def register_listeners(scheduler, listeners):

    for name,listener in listeners.iteritems():
        if listener.get('enable', True):
            scheduler.add_listener(listener['obj'].respond, 
                            listener.get('event_mask', 511))
            logging.info("Listener %s registered." % name)
        else:
            logging.info("Listener %s not registered." % name)

def main():
    ''' Description
            Reads configurations, setup tasks, schedule tasks with 
            apscheduler then daemonize 
        Arguments:
        Returns:
    '''
    tasklist = {} #list of scheduled tasks
    listeners = {} #list of listener tasks
    
#     parser = argparse.ArgumentParser()
#     parser.add_argument("-c", "--conf", help="define config file to read")
#     args = parser.parse_args()
    
    # Perform configuration extractions  
    log_conf = settings.log_conf
    
    #setup basic logging
    configure_logging(log_conf)
    logging.info("logging configured")
   
    #parse tasks and build tasklist 
    for name, task in settings.tasks.iteritems():
        martial_task(name, task, tasklist)
    #parse listeners build listeners list
    for name, task in settings.listeners.iteritems():
        martial_listener(name, task, listeners)
       
    scheduler = BackgroundScheduler(); #embedded mode
    schedule_tasks(scheduler, tasklist)
    register_listeners(scheduler, listeners)
    scheduler.start()
    
    while True:
        time.sleep(10);

if __name__ == '__main__':

    ''' Module called as script, parse args decide to run test or main'''
    main()