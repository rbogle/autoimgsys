from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton
import logging

class Plugin(IPlugin):
    
    def __init__(self):
        
        super(Plugin, self).__init__()
        manager = PluginManagerSingleton.get()
        self.app = manager.app
    
    def activate(self):
        super(Plugin, self).activate()
        logging.info("Plugin: %s activated" % self.__class.__name__)
        
    def deactivate(self):
        super(Plugin, self).deactivate()
        logging.info("Plugin: %s deactivated" % self.__class.__name__)    