from plugin import PluginObj
from relay import Relay
import logging
import importlib

logger = logging.getLogger(__name__)

class Task(PluginObj):

    def __init__(self, **kwargs):
        super(Task,self).__init__()
        vars(self).update(kwargs)
        self.initialized = False
        
    def configure(self, **kwargs):
        """ 
            Called when scheduled as a timed event
        """
        raise NotImplementedError
    
    def run(self, **kwargs):
        """ 
            Called when run as a timed event
        """
        raise NotImplementedError
    
    def get_config_properties(self):
        """ 
            Called to confirm valid config elements
            should return list of  tuples. Each tuple should be
            (property name, pretty name, description)
            These will be used in the ui
        """
        raise NotImplementedError
        
    def get_run_properties(self):
        """ 
            Called to confirm valid config elements
            should return list of  tuples. Each tuple should be
            (property name, pretty name, description)
            These will be used in the ui
        """
        raise NotImplementedError
        
    def _marshal_obj(self, obj_name, **kwargs):
   
        obj_args = kwargs.get(obj_name, {});
        obj = None
        # instantiate class 
        try:
            obj_mod= importlib.import_module(obj_args.get('module'))
            obj_cls = getattr(obj_mod, obj_args.get('class'))
            #TODO test for and pass init_args
            obj = obj_cls()
            
        except AssertionError:
            logger.error("Specified class %s is not a Relay" % obj_args.get('class'))
            
        except Exception as e:   
            logger.error("error: %s" % type(e))
            logger.error("Could not build class %s" % obj_args.get('class'))
        
        return obj
        
class PoweredTask(Task):
    
    def set_relay_plugin(self, relay):
        if isinstance(relay, Relay):
            self._powerctrlr = relay
            
    def set_relay_delay(self, delay_secs):
            self._powerdelay = delay_secs    
    
    def set_relay_port(self, port):
            self._powerport = port
        
    def _power(self, powerstate=False):
        
        if self._powerctlr is not None:
            try:
                self._powerctlr.set_port(self._powerport, powerstate)
            except Exception as e:
                logger.error(str(e))                 
        else:        
            logger.error("No power controller is configured.")