#external deps
from yapsy.PluginManager import PluginManagerSingleton
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext import admin
from flask.ext.admin.contrib import sqla
from collections import namedtuple
# local package
from ais.lib.task import Task, PoweredTask
from ais.lib.auditor import Auditor
from ais.lib.relay import Relay
#from ais.ui import config as uiconfig
#from ais.ui.views import *

from ais.ui import config, flask, db
from ais.ui.models import *
from ais.ui.views import *
#standard deps
import os
import logging

logger = logging.getLogger(__name__)

class AISApp(object):
    
    def start(self):
        if self.flask is not None:
            self.flask.run()
    
    def stop():
        pass
    
    def reload():
        pass
    
    def __init__(self, plugin_location="ais/plugins"):
        
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
        
        #setup web ui based on Flask, Flask-Admin, Flask-SQLAlchemy
        self.flask = flask
        self.db = db
        self.database_file = config.DATABASE_PATH+config.DATABASE_FILE
        
#        self.flask = Flask("ais")
#        #TODO config Flask here
#        self.flask.config.from_object(uiconfig)
#
#        app_dir = os.path.realpath(os.path.dirname(__file__))
#        self.database_path = self.flask.root_path+self.flask.config['DATABASE_FILE']
#        
#        self.flask.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+ self.database_path      
#        logger.info("Flask Config DB URI %s" %self.flask.config['SQLALCHEMY_DATABASE_URI'])
#        self.db = SQLAlchemy(self.flask)
    
        #Basic flow for building the dashboard from plugins    
        plugin = namedtuple('plugin', 'name widget')
        plugins = ( plugin("test1","<a href='/'>test1widget</a>"), plugin("test2", "<a href='/'>test2widget</a>") )

        #DashboardView displays info from plugins on index page
        dv = DashboardView(url='/')
        dv.register_plugins(plugins)
        
        self.ui = admin.Admin(self.flask, 'Automated Imaging System', 
                        index_view=dv,
                        url='/', 
                        static_url_path="/admin",
                        template_mode='bootstrap3'
            )
                        
        self.ui.add_view(sqla.ModelView(Job,db.session, name='Jobs'))
        self.ui.add_view(sqla.ModelView(Auditor,db.session, name='Auditors'))
        self.ui.add_view(sqla.ModelView(User,db.session, category='Advanced')) 
        self.ui.add_view(ConfigurableView(Plugin,db.session,name='Plugins', category='Advanced'))
        self.ui.add_view(ConfigurableView(Action,db.session,name='Actions', category='Advanced'))
        self.ui.add_view(sqla.ModelView(Schedule,db.session, name = 'Schedules',category='Advanced'))

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
    
        test_schedule = Schedule(name="Every10min", minute="*/10")
        test_ia = { 
                'power_ctlr':{
                    'module': 'ais.sensors.phidget',
                    'class': 'Phidget'
                },
                'power_delay': 5
            }
        test_plugin = Plugin(name="Test", module_name= 'ais.test.test_task',
                             class_name='Test_Task',
                             args = test_ia
                        )
    
        test_ra = { 'file_name': 'HDR_test', 'sequence': [
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
                }                
        
        test_action = Action(name="Run Test", plugin=test_plugin, args=test_ra)                
    
        self.db.session.add(test_schedule)
        self.db.session.add(test_plugin)
        self.db.session.add(test_action)
        
        self.db.session.commit()
        return


if __name__=='__main__':
    #logging config
    logging.basicConfig(level=logging.INFO)
     
    app = AISApp()     
     
    # Build a sample db on the fly, if one does not exist yet.
    logger.info("DB path is: %s" % app.database_file)   
    logger.info("Flask root is: %s" %app.flask.root_path)
    if not os.path.exists(app.database_file):
        logger.info("Initializing DB")
        app.initialize_db()    
    
    app.start()
    
 