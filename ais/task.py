import logging
import importlib

class Task(object):

    def __init__(self, **kwargs):
        vars(self).update(kwargs)
    
    def run(self, **kwargs):
        """ Called when registered as a timed event
        """
        raise NotImplementedError
        
    def respond(self, event):
        """ Called when registered as a event listener.
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
            logging.error("Specified class %s is not a Relay" % obj_args.get('class'))
            
        except Exception as e:   
            logging.error("error: %s" % type(e))
            logging.error("Could not build class %s" % obj_args.get('class'))
        
        return obj