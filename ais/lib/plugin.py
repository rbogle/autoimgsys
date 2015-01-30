from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton
from flask.ext.admin import BaseView, expose
from flask import render_template
import logging, inspect

class PluginObj(IPlugin, BaseView):
    
    def __init__(self, **kwargs):
        
        IPlugin.__init__(self)
        BaseView.__init__(self, **kwargs)
        self.manager = PluginManagerSingleton.get()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = False
        
        self.viewable = False
        self.widgetized = False
        self.use_filestore = False
        self.use_sqllog = False
    
        #set defaults for template paths
        # ais/plugins/name/widget.html
        # ais/plugins/name/index.html
        path_items = inspect.getfile(self.__class__).split('/')[-3:-1]
        self.path = str.join('/',path_items)
        self.view_template = self.path+'/index.html'
        self.widget_template = self.path+'/widget.html'
        self.url="/"+self.__class__.__name__.lower()+"/"
        self.filestore = None
        
        try: 
            getattr(self.manager, 'app')
        except Exception:
            pass
        else:
            self.app = self.manager.app
        self.logger.debug("%s Init finished", self.__class__.__name__)

    def is_accessible(self):
        '''
            Makes viewable plugins appear and disappear as enabled/disabled        
        '''
        return self.enabled
        
    def activate(self):
        super(PluginObj, self).activate()
        self.logger.debug("Plugin: %s activated" % self.__class__.__name__)
        
    def deactivate(self):
        super(PluginObj, self).deactivate()
        self.logger.debug("Plugin: %s deactivated" % self.__class__.__name__)
        
    def widget_view(self):
        template = self.widget_template
        return render_template(template, data=self)
        
    def get_configs(self):
        '''
            get_configs returns a list of Config objects that
            the plugin wants to seed the db with. 
        '''
        return list()
        
    @expose('/')
    def plugin_view(self):
        template = self.view_template
        return self.render(template, data=self)