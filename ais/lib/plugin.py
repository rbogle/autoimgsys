from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton
from flask.ext.admin import BaseView, expose
from flask import render_template
import logging, inspect, os.path

logger = logging.getLogger(__name__)

class PluginObj(IPlugin, BaseView):
    
    def __init__(self, **kwargs):
        
        IPlugin.__init__(self)
        BaseView.__init__(self, **kwargs)
        manager = PluginManagerSingleton.get()
        
        self.viewable = False
        self.widgetized = False
        self.enabled = False
        
        path_items = inspect.getfile(self.__class__).split('/')[-3:-1]
        path = str.join('/',path_items)
        self.view_template = path+'/index.html'
        self.widget_template = path+'/widget.html'
        
        try: 
            getattr(manager, 'app')
        except Exception,e:
            pass
        else:
            self.app = manager.app

    def is_accessible(self):
        return self.enabled
        
    def activate(self):
        super(Plugin, self).activate()
        logger.info("Plugin: %s activated" % self.__class__.__name__)
        
    def deactivate(self):
        super(Plugin, self).deactivate()
        logger.info("Plugin: %s deactivated" % self.__class__.__name__)
        
    def widget_view(self):
        template = self.widget_template
        return render_template(template, data=self)
    
    @expose('/')
    def plugin_view(self):
        template = self.view_template
        return self.render(template, data=self)