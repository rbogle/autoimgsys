from plugin import PluginObj
from relay import Relay
import logging
import importlib

logger = logging.getLogger(__name__)

class Task(PluginObj):

    def __init__(self, **kwargs):
        super(Task,self).__init__()
        vars(self).update(kwargs)
    
    def configure(self, **kwargs):
        vars(self).update(kwargs)
    
    def run(self, **kwargs):
        """ Called when registered as a timed event
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