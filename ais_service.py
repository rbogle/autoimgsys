#!/usr/bin/python

#external deps
from yapsy.PluginManager import PluginManagerSingleton
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext import admin
from flask.ext.admin.contrib import sqla
from flask.ext.admin.contrib.fileadmin import FileAdmin
from apscheduler.schedulers.background import BackgroundScheduler

# local packages
from ais.lib.task import Task, PoweredTask
from ais.lib.listener import Listener
from ais.lib.relay import Relay
from ais.ui import config, flask, db
from ais.ui.models import *
from ais.ui.views import *

#standard deps
import os, copy, logging

logger = logging.getLogger(__name__)

class AISApp(object):
    
    def run(self):
        #fset host to 0.0.0.0 to show interface on all ips
        # need to setup ngix or apache and use wgsi
        self.flask.run(host="0.0.0.0")
    
    def pause(self):
        logger.debug("AISApp pause called")
        if self.running:
            self.pause_jobs()
            self.running = False
            
    def resume(self):
        logger.debug("AISApp resume called")
        if not self.running:
            self.resume_jobs()
            self.running = True
    
    def get_status(self):
        if self.running:
            msg = "Scheduler is Running"
        else:
            msg = "Scheduler is Paused"
        return (self.running, self.get_num_active_jobs(), msg)
        
    def get_num_active_jobs(self):     
        if self.running: #get jobs scheduled
            return len(self.scheduler.get_jobs())
        else: #get enabled jobs from db    
            return len(Job.query.filter_by(enabled=True).all())
            
    def pause_jobs(self):
        '''
            iterates through aps joblist and calls pause, 
            sets running status in db.       
        '''
        aps_jobs = self.scheduler.get_jobs()
        for apsjob in aps_jobs:
            apsjob.pause()
            Job.query.get(int(apsjob.id)).running=False
        db.session.commit()
      
    def resume_jobs(self):
        '''
            iterates through aps joblist and calls resume, 
            sets running status in db.
        '''        
        aps_jobs = self.scheduler.get_jobs()
        for apsjob in aps_jobs:
            apsjob.resume()
            dbsjob = Job.query.get(int(apsjob.id))
            if dbsjob is not None:
                dbsjob.running=True
        db.session.commit()
    
    def initalize_plugins(self):
        logger.debug("Initializing enabled plugins....")
        pdb = Plugin.query.filter_by(category='Task',enabled=True).all()
        for p in pdb:
            self.initalize_plugin(p.name)
        
    def initalize_plugin(self, name):
        logger.debug("Initializing plugin %s"%name)
        pi = self.plugin_manager.getPluginByName(name, 'Task')
        if pi is not None:
            po = pi.plugin_object
            logger.debug("Found plugin...")
            if not po.initalized:
                #get initalize config and pass to
                logger.debug("Plugin not initalized")
                cfg = Config.query.filter_by(plugin=name, role="Initalize").first()
                if cfg is not None:
                    logger.debug("Config args: %s"%(cfg.args))
                    po.configure(**cfg.args)
            else:
                logger.debug("Plugin already initalized")
        
    def sync_plugin_status(self, name, status):
        '''
            Pick up any change in UI for plugin.enabled and sync to 
            actual plugin object. Called from PluginView.updateModel.
        '''
        pl = self.plugin_manager.getAllPlugins()
        for pi in pl:
            if pi.name == name:
                pi.plugin_object.enabled = status
    
    def sync_plugin_db(self):
        '''
            sync_plugin_db crosschecks loaded plugins with list of plugins in DB
            and adds any missing plugins, and removes and unloaded plugins. 
        '''

        for cat in self.plugin_manager.getCategories():  
            
            pilist = self.plugin_manager.getPluginsOfCategory(cat)
            pinames = {pi.name:pi.plugin_object for pi in pilist}
            pdblist = Plugin.query.filter_by(category=cat).all() 
            pdbnames = [p.name for p in pdblist]
            
            for pdb in pdblist: #walk the db 
                if pdb.name not in pinames.keys(): #plugin no longer loaded
                    logger.debug("Removing plugin %s from db" %pdb.name)
                    db.session.delete(pdb)
                else:
                    pinames[pdb.name].enabled = pdb.enabled                    
                self.db.session.commit()   
                
            for pi in pilist: #walk the plugins
                logger.debug("Checking plugin %s is in db"%pi.name)
                if pi.name not in pdbnames: #not in db create and add
                    po = pi.plugin_object
                    logger.debug("plugin syncing for cat %s, plugin name is %s" %(cat,pi.name))
                    pdb = Plugin( 
                            name= pi.name, 
                            class_name = po.__class__.__name__,
                            category = cat,
                            enabled = False
                            )
                    self.db.session.add(pdb)
                self.db.session.commit()
        
    def schedule_jobs_from_db(self):
        '''
            looks in database for jobs enabled and loads them into the job scheduler
            unschedules jobs that are disabled. Running status is updated. 
            jobs are unique based id so the db and scheduler should stay in sync
            
        ''' 
        logger.debug("AISApp schedule_jobs_from_db called")
        joblist = Job.query.all()
        
        for job in joblist:
            if job.enabled:
                 if self.schedule_job(job):
                     logger.debug("Job scheduled: %s" %job)
                 else: 
                     logger.debug("Job %s could not be scheduled." %job)
            else:
                self.unschedule_job(job)
                logger.debug("Job unscheduled: %s" %job)
            logger.debug("Job db status is: %s" % job.running)   
        #sync running status in db    
        db.session.commit()     
        return joblist
        
    def register_listeners_from_db(self):
        '''
            looks in database for Auditors enabled and registers the listener
            with APScheduler. If disabled attempts to unregister.
        '''         
        listeners = Auditor.query.all()
        #clean listener stack, safest way to dump listeners
        with self.scheduler._listeners_lock:
            self.scheduler._listeners=list()
        #now register all enabled listeners  
        for listener in listeners:
            if listener.enabled:
                self.register_listener(listener)        
        return listeners  

    def schedule_job(self, job):
        '''
            schedule_job takes a db.model Job and schedules corresponding aps job 
            using Schedule, Job and Plugin info to configure plugin and job. 
            aps jobs are not duplicated just overwritten. 
        '''
        task_name = job.action.plugin.name
        task_args = job.action.config.args
        trigger_args = job.schedule.get_args()
        
        task_obj = self.plugin_manager.getPluginByName(task_name,'Task').plugin_object

        aps_job = self.scheduler.get_job(str(job.id))
        
        if aps_job is None:    
            try:   
                aps_job =self.scheduler.add_job(
                                task_obj.run, 
                                'cron', 
                                kwargs = task_args, 
                                id=str(job.id), 
                                name=job.name, 
                                replace_existing=True,
                                coalesce = True,
                                max_instances=1,
                                **trigger_args
                                )
            
            except Exception as e:
                logger.debug("Job scheduler exception: %s" %e)
                logger.info("Job %s could not be scheduled" %job.id)
                job.running = False
                return False
            logger.info("Job %s has been scheduled" %job.id)
            
        if not self.running:
            # The scheduler is in pause state so pause this job too
            job.running = False
            aps_job.pause()
        else:
            job.running = True
        return True
                               
    def unschedule_job(self, job):
        '''
            unschedule_job take db.model Job and removes the scheduled aps job
            of the same id from the scheduler
        '''
        try:
            self.scheduler.remove_job(str(job.id))
        except: 
            logger.error("Job %s could not be removed from jobstore" %job.id)
        else:
            logger.info("Job %s has been unscheduled" %job.id)
            job.running = False
               
    def register_listener(self, auditor):
        '''
            register_listener takes a db.model Auditor and connects a Listener
            plugin to the APS event model to catch events. 
        '''       
        listener_name = auditor.plugin.name
        listener_obj = self.plugin_manager.getPluginByName(listener_name,'Listener').plugin_object
        event_mask = auditor.event_mask
        try:
            self.scheduler.add_listener(listener_obj.respond, event_mask)
        except:
            logger.error("Auditor %s could not be registered" %auditor.name)
        else:
            logger.info("Auditor %s is registered" %auditor.name)
                
    def unregister_listener(self, auditor):
        '''
            unregister_listener takes a db.model Auditor and disconnects a Listener
            plugin from the APS event model to catch events. 
        '''
       
        listener_name = auditor.plugin.name
        listener_obj = self.plugin_manager.getPluginByName(listener_name,'Listener').plugin_object
        try:
            self.scheduler.remove_listener(listener_obj.respond)
        except:
            logger.error("Auditor %s could not be unregistered" %auditor.name)
        else:
            logger.info("Auditor %s is unregistered" %auditor.name)

    def get_active_task_names():
        choices = list()
        pdbs = db.session.query(Plugin).filter_by(category="Task", enabled=True).all()
        for p in pdbs:
            choices.append((p.name, p.name))
        return choices
                
    def initalize_db(self):
        """
        Populate empty db with default entries.
        """
        self.db.drop_all()
        self.db.create_all()
        # build plugin db
        self.sync_plugin_db()
        #TODO load defaults from a config file
        
        test_user = User(login="test", password="test")
        self.db.session.add(test_user)
        
        cr = Config(name='Run Config', plugin='Test Task', role="Runtime", args={'arg1':"first arg", 'arg2':"second arg"})
        ci = Config(name='Task Init', plugin='Test Task', role="Initalize", args={'arg1':"primata arg", 'arg2':"secunda arg"})
        self.db.session.add(cr)
        self.db.session.add(ci)
        self.db.session.add(Action(name='Run Test',config=cr))        
        self.db.session.add(Schedule(name='Every 2 Minutes', minute='*/2'))
        self.db.session.commit()
                           
    def __init__(self, plugin_location=flask.root_path+"/plugins"):
      
        #setup web ui based on Flask, Flask-Admin, Flask-SQLAlchemy
        self.flask = flask
        #pass aisapp instance back to flask for syncing
        flask.aisapp = self
        
        logging.debug("Flask root %s" %self.flask.root_path)
        self.db = db
        self.database_file = config.DATABASE_PATH+config.DATABASE_FILE
        
            
        #setup plugin management and discovery
        plugin_manager = PluginManagerSingleton.get()
        self.plugin_manager = plugin_manager
        plugin_manager.setPluginPlaces([plugin_location])
        plugin_manager.setCategoriesFilter({
            "Listener" : Listener,            
            "Task" : Task,
            "Relay" : Relay
        })
        
        plugin_manager.app = self #pass app ref back to plugins.
        plugin_manager.collectPlugins()

        #setup databse defaults if it doesn't exist
        if not os.path.exists(self.database_file):
            logger.info("Initializing DB")
            self.initalize_db()

        #add apscheduler and start it. 
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.running = True
                         
        #cross check with DB to see if plugins are avail in ui
        self.sync_plugin_db()
        self.initalize_plugins()
        
        #examine db for jobs configured and enables and load them into APS
        self.schedule_jobs_from_db()
        self.register_listeners_from_db()
        
        #DashboardView displays info from plugins on index page
        dv = DashboardView(url='/')
        
               #build web ui
        self.ui = admin.Admin(self.flask, 'Automated Imaging System', 
                        index_view=dv,
                        url='/', 
                        static_url_path="/admin",
                        template_mode='bootstrap3'
            )  
            
        #add Scheduling Menu
        self.ui.add_view(JobView(Job,db.session, name='Scheduled Jobs'))

        #Make Plugins menu
        #find plugins with views and widgets available:
        for pi in plugin_manager.getAllPlugins():
            po = pi.plugin_object
            po.name = pi.name
            po.filestore = config.FILESTORE+"/"+pi.name
            try: 
                os.mkdir(po.filestore)
            except Exception as ex:
                logger.error('Failed to create plugin filestore %s' %ex)
            logger.debug("Assessing Plugin: %s for UI" %pi.name)
            if po.widgetized:
                logger.debug("Plugin widgetized: %s" %pi.name)
                dv.register_plugin(po)
            if po.viewable:
                #register url view and add to Plugins Menu
                logger.debug("Plugin Viewable: %s" %pi.name)
                po.category= "Plugins"
                self.ui.add_view(po) 
        
        
        self.ui.add_view(FileAdmin(config.FILESTORE, name="Files"))
        #Schedule Settings menu
        self.ui.add_view(AuditorView(Auditor,db.session, name='Auditor List', category="Schedule Settings"))
        self.ui.add_view(AisModelView(Schedule,db.session, name = 'Schedules',category='Schedule Settings'))
        self.ui.add_view(ActionView(Action,db.session,name='Actions', category='Schedule Settings'))   
        #add Advanced Menu
        self.ui.add_view(AisModelView(User,db.session, category='Advanced')) 
        self.ui.add_view(PluginView(Plugin,db.session,name='Plugins', category='Advanced'))
        self.ui.add_view(ConfigView(Config,db.session,name='Configs', category='Advanced'))

if __name__=='__main__':
    #logging config
    logging.basicConfig(level=logging.DEBUG)
    #setup and start the app
    app = AISApp()    
    app.run()
    
    