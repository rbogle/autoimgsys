#external deps
from yapsy.PluginManager import PluginManagerSingleton
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext import admin
from flask.ext.admin.contrib import sqla
from apscheduler.schedulers.background import BackgroundScheduler

# local package
from ais.lib.task import Task, PoweredTask
from ais.lib.auditor import Auditor
from ais.lib.relay import Relay
from ais.ui import config, flask, db
from ais.ui.models import *
from ais.ui.views import *

#standard deps
import os, copy, logging


logger = logging.getLogger(__name__)

class AISApp(object):
    
    def start(self):
        if self.flask is not None:
            self.flask.run()
    
    def stop(self):
        pass
    
    def restart(self):
        pass
    
    def sync_plugin_db(self):
        '''
            sync_plugin_db crosschecks loaded plugins with list of plugins in DB
            and adds any missing plugins. 
        '''
        for cat in self.plugin_manager.getCategories():           
            for pi in self.plugin_manager.getPluginsOfCategory(cat):
                po = pi.plugin_object
                pdb = Plugin.query.filter_by(class_name=po.__class__.__name__).first() 
                #If plugin not found add it in
                if pdb is None: 
                    pdb = Plugin( 
                        name= pi.name, 
                        class_name = po.__class__.__name__,
                        category = cat                       
                        )
                    self.db.session.add(pdb)
                    self.db.session.commit()
        
    
    def schedule_jobs_from_db(self):
        '''
            looks in database for jobs enabled and loads them into the job scheduler
            unschedules jobs that are disabled. Running status is updated. 
        ''' 
        logger.debug("AISApp schedule_jobs_from_db called")
        joblist = Job.query.all()
        
        for job in joblist:
            if job.enabled:
                self.schedule_job(job)
                logger.debug("Job scheduled: %s" %job)
            else:
                self.unschedule_job(job)
                logger.debug("Job unscheduled: %s" %job)
            logger.debug("Job db status is: %s" % job.running)    
        self.db.session.commit()        
        
        return joblist
  
    def initialize_db(self):
        """
        Populate empty db with default entries.
        """
        self.db.drop_all()
        self.db.create_all()
        # passwords are hashed, to use plaintext passwords instead:
        # test_user = User(login="test", password="test")
        test_user = User(login="test", password="test")
        self.db.session.add(test_user)
        self.db.session.add(Plugin(name='Test_Task', class_name='Test_Task', category='Task', id=3))
        self.db.session.add(Action(name='Run Test', args={'arg1' : 'first arg', 'arg2' : 'second arg'}, plugin_id=3))        
        self.db.session.add(Schedule(name='Every 2 Minutes', minute='*/2'))
        self.db.session.commit()
        return      

    def schedule_job(self, job):
        
        task_name = job.action.plugin.name
        task_args = job.action.args
        trigger_args = job.schedule.get_args()
        
        task_obj = self.plugin_manager.getPluginByName(task_name,'Task').plugin_object
        try:
            self.scheduler.add_job(
                            task_obj.run, 
                            'cron', 
                            kwargs = task_args, 
                            id=str(job.id), 
                            name=job.name, 
                            replace_existing=True,
                            **trigger_args
                            )
        except:
            logger.info("Job %s could not be scheduled" %job.id)
            job.running = False
        else:
            logger.info("Job %s has been scheduled" %job.id)
            job.running =True
                               
    def unschedule_job(self, job):
        try:
            self.scheduler.remove_job(str(job.id))
        except: 
            logger.error("Job %s could not be removed from jobstore" %job.id)
        else:
            logger.info("Job %s has been unscheduled" %job.id)
            job.running = False
               
    def register_listener(self, auditor):
    
            if listener.get('enable', True):
                scheduler.add_listener(listener['obj'].respond, 
                                listener.get('event_mask', 511))
                logging.info("Listener %s registered." % name)
            else:
                logging.info("Listener %s not registered." % name)

    
    def __init__(self, plugin_location="ais/plugins"):

        
        #setup web ui based on Flask, Flask-Admin, Flask-SQLAlchemy
        self.flask = flask
        #pass aisapp instance back to flask for syncing
        flask.aisapp = self
        
        self.db = db
        self.database_file = config.DATABASE_PATH+config.DATABASE_FILE
                
        #setup plugin management and discovery
        plugin_manager = PluginManagerSingleton.get()
        self.plugin_manager = plugin_manager
        plugin_manager.setPluginPlaces([plugin_location])
        plugin_manager.setCategoriesFilter({
            "Task" : Task,
            "Auditor" : Auditor,
            "Relay" : Relay
        })
        
        plugin_manager.app = self #pass app ref back to plugins.
        plugin_manager.collectPlugins()

        #add apscheduler
        self.scheduler = BackgroundScheduler()

        #setup databse defaults if it doesn't exist
        if not os.path.exists(self.database_file):
            logger.info("Initializing DB")
            self.initialize_db()                 
              
        #cross check with DB to see if plugins are avail in ui
        self.sync_plugin_db()

        #examine db for jobs configured and enables and load them into APS
        self.schedule_jobs_from_db()
        
        #DashboardView displays info from plugins on index page
        dv = DashboardView(url='/')
        
               #build web ui
        self.ui = admin.Admin(self.flask, 'Automated Imaging System', 
                        index_view=dv,
                        url='/', 
                        static_url_path="/admin",
                        template_mode='bootstrap3'
            )  

        self.ui.add_view(JobView(Job,db.session, name='Job List'))
        self.ui.add_view(sqla.ModelView(Auditor,db.session, name='Auditor List'))
            
        #find plugins with views and widgets available:
        for pi in plugin_manager.getAllPlugins():
            po = pi.plugin_object
            if po.widgetized:
                dv.register_plugin(po)
            if po.viewable:
                #register url view and add to Plugins Menu
                po.category= "Plugins"
                self.ui.add_view(po) 
                
        #add Advanced Menu
        self.ui.add_view(sqla.ModelView(User,db.session, category='Advanced')) 
        #self.ui.add_view(ConfigurableView(Plugin,db.session,name='Plugins', category='Advanced'))
        self.ui.add_view(ConfigurableView(Action,db.session,name='Actions', category='Advanced'))
        self.ui.add_view(sqla.ModelView(Schedule,db.session, name = 'Schedules',category='Advanced'))

if __name__=='__main__':
    #logging config
    logging.basicConfig(level=logging.DEBUG)
    #setup and start the app
    app = AISApp()     
    app.start()
    
 