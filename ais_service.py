#!/usr/bin/python

#external deps
from yapsy.PluginManager import PluginManagerSingleton
from flask.ext import admin
from flask.ext.admin.contrib.fileadmin import FileAdmin
from apscheduler.schedulers.background import BackgroundScheduler

# local packages
from ais.lib.fileadmin import AisFileAdmin
from ais.lib.task import Task
from ais.lib.listener import Listener
from ais.lib.relay import Relay
from ais.lib.sqllog import SQLAlchemyHandler
from ais.ui import config, flask, db
from ais.ui.models import *
from ais.ui.views import *
from ais import __version__

#standard deps
import os, logging, logging.config

#logging config
logging.config.dictConfig(config.LOGGING)
logger = logging.getLogger(__name__)

class AISApp(object):
    
    def run(self):
        #fset host to 0.0.0.0 to show interface on all ips
        # TODO need to setup ngix or apache and use wgsi?
        self.flask.run(host="0.0.0.0", port=config.PORT, use_reloader=config.USE_RELOADER)
    
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
                plg = Plugin.query.filter_by(name=name).first()
                cfg = Config.query.filter_by(plugin_id=plg.id, role="Initalize").first()
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
                #disabling plugin so remove jobs using it
                if not status:
                    pdb = Plugin.query.filter_by(name=pi.name).first()
                    self.remove_plugin_jobs(pdb.id)
                
    def remove_plugin_jobs(self, id):
        jobs = Job.query.join(Config).filter(Config.plugin_id==id)
        for job in jobs:
            self.unschedule_job(job)
            self.db.session.delete(job)
        self.db.session.commit()
    
    def sync_plugin_db(self):
        '''
            sync_plugin_db crosschecks loaded plugins with list of plugins in DB
            and adds any missing plugins, and removes and unloads plugins. 
        '''

        for cat in self.plugin_manager.getCategories():  
            
            pilist = self.plugin_manager.getPluginsOfCategory(cat)
            pinames = {pi.name:pi.plugin_object for pi in pilist}
            pdblist = Plugin.query.filter_by(category=cat).all() 
            pdbnames = [p.name for p in pdblist]
            pdbids = [p.id for p in pdblist]
            
            #walk the jobs and remove any orphans
            if cat=="Task":
                jobs = Job.query.all()
                for job in jobs:
                    if job.config.plugin_id not in pdbids:
                        self.unschedule_job(job)
                        self.db.session.delete(job)                
                self.db.session.commit()    
            
            #walk the db remove ones not loaded by pm
            for pdb in pdblist: 
                if pdb.name not in pinames.keys(): #plugin no longer loaded
                    logger.debug("Removing plugin %s from db" %pdb.name) 
                    self.remove_plugin_jobs(pdb.id)
                    #remove configs for this plugin
                    cfgs = Config.query.filter_by(plugin=pdb).all()
                    for cfg in cfgs:
                        db.session.delete(cfg)
                    db.session.delete(pdb)
                else:
                    pinames[pdb.name].enabled = pdb.enabled                    
            self.db.session.commit()
            #walk the plugins and insert into db new plugins    
            for pi in pilist: 
                logger.debug("Checking plugin %s is in db"%pi.name)
                if pi.name not in pdbnames: #not in db create and add
                    po = pi.plugin_object
                    logger.debug("plugin syncing for cat %s, plugin name is %s" %(cat,pi.name))
                    pdb = Plugin( 
                            name= pi.name, 
                            class_name = po.__class__.__name__,
                            category = cat,
                            enabled = po.enabled
                            )
                    self.db.session.add(pdb)
                    #add default configs if po has them.
                    for cfg in po.get_configs():
                        cfg.plugin = pdb
                        self.db.session.add(cfg)
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
        task_name = job.config.plugin.name
        task_args = job.config.args
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
        
        self.db.session.add(Schedule(name='Every 10 Minutes', minute='*/10', hour='6-18'))
        self.db.session.commit()
                           
    def __init__(self, plugin_location=flask.root_path+"/plugins"):
        
        #setup web ui based on Flask, Flask-Admin, Flask-SQLAlchemy
        self.flask = flask
        #pass aisapp instance back to flask for syncing
        flask.aisapp = self
        logger.info("AIS servic starting up!")
        logger.debug("Flask root %s" %self.flask.root_path)
        self.db = db
        self.database_file = config.DATABASE_PATH+config.APP_DATABASE_FILE
        #self.seed_db = False
            
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
            #self.seed_db = True

        #make sure filestore exists for FileAdmin and plugins
        if not os.path.isdir(config.FILESTORE):    
            try:
                logger.debug("Attempting to makedir: %s" %config.FILESTORE)
                os.makedirs(config.FILESTORE)
            except OSError as oserr:
                if not os.path.isdir(config.FILESTORE):
                    logger.error("Ais_Service cannot mkdir %s" %config.FILESTORE)
                    raise oserr
                    
        #add apscheduler and start it. 
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.running = True
                         
        #cross check with DB to see if plugins are avail in ui
        self.sync_plugin_db()
        self.initalize_plugins()

        #examine db for jobs configured and enabled and load them into APS
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
        self.ui.hostname = config.HOSTNAME
        
        #add Scheduling Menu
        self.ui.add_view(JobView(Job,db.session, name='Tasks'))
        self.ui.add_view(ModelView(Schedule,db.session, name = 'Schedules'))
        self.ui.add_view(AisFileAdmin(config.DISKSTORE, endpoint="data",name="Data"))
        
        #sqlloghdlr created for plugin use
        sqlloghdlr = SQLAlchemyHandler()
        sqlloghdlr.setLevel(logging.DEBUG)
        sqlloghdlr.setFormatter(logging.Formatter())        
        
        
        #Make Plugins menu
        #find plugins with views and widgets available:
        logger.debug("Setting up plugins")

        for pi in plugin_manager.getAllPlugins():
            logger.debug("Processing Plugin %s", pi.name)
            po = pi.plugin_object
            po.name = pi.name
            
            #give each plugin its own sqllog in its own table 
            if po.use_sqllog:            
                logger.debug("Config sqllog handler to plugin logger")
                po.logger.addHandler(sqlloghdlr)
            #give each plugin a directory in the filestore if they want it. 
            if po.use_filestore :
                logger.debug("Creating plugin filestorage structures")
                po.filestore = config.FILESTORE+"/"+pi.name
                if not os.path.isdir(po.filestore):    
                    try:
                        logger.debug("Attempting to makedir: %s" %po.filestore)
                        os.makedirs(po.filestore)
                    except OSError:
                        if not os.path.isdir(po.filestore):
                            po.filestore = None
                            logger.error("Ais_Service cannot mkdir %s" %po.filestore)
                        
            logger.debug("Assessing Plugin: %s for UI" %pi.name)
            if po.widgetized:
                logger.debug("Plugin widgetized: %s" %pi.name)
                dv.register_plugin(po)
            if po.viewable:
                #register url view and add to Plugins Menu
                logger.debug("Plugin Viewable: %s" %pi.name)
                po.category= "Modules"
                self.ui.add_view(po) 
                
        # Schedule Settings menu
        # Event monitoring disabled for now
        #self.ui.add_view(AuditorView(Auditor,db.session, name='Event Handlers', category="Settings"))
        #self.ui.add_view(ModelView(Schedule,db.session, name = 'Task Schedules',category='Settings'))
        
        #add Advanced/Admin Menu
        # TODO needs to have user auth module to protect
        #self.ui.add_view(ModelView(User,db.session, name='Users', category='Admin')) 
        self.ui.add_view(EventView(Event,db.session,name='Event Logs', category='Admin'))
        self.ui.add_view(PluginView(Plugin,db.session,name='Module Admin', category='Admin'))         
        self.ui.add_view(LogView(Log,db.session, name='Module Logs', category='Admin')) 
        self.ui.add_view(ConfigView(Config,db.session,name='Module Confs', category='Admin'))
        

if __name__=='__main__':

    #setup and start the app
    app = AISApp()    
    app.run()
    
    