# -*- coding: utf-8 -*-

from ais.lib.relay import Relay
from Phidgets.PhidgetException import PhidgetException
from Phidgets.Devices.InterfaceKit import InterfaceKit


class Phidget(Relay):
    
    def __init__(self, **kwargs):
        super(Phidget,self).__init__(**kwargs)
        self.use_sqllog = True
    
    def get_port(self, port):
        rval = -1
        if self.connect():
            try:
                rval = self.interfaceKit.getOutputState(port)
            except PhidgetException as e:
                self.logger.error("Phidget Exception %i: %s" % (e.code, e.details))
                raise e
            finally:
                self.disconnect()
        return rval
    
    def set_port(self, port, state):
        if self.connect():
            try:
                self.interfaceKit.setOutputState(port, state)
            except PhidgetException as e:
                self.logger.error("Phidget Exception %i: %s" % (e.code, e.details))
                raise e
            finally:
                self.disconnect()
            return True
        else:
            return False            
            
    def connect(self):
        #Create an interfacekit object
        try:
            self.interfaceKit = InterfaceKit()
            self.interfaceKit.openPhidget()
            self.interfaceKit.waitForAttach(10000)
            
        except RuntimeError as e:
            self.logger.error("Runtime error: %s" % e.message)
            raise e
            
        except PhidgetException as e:
            self.logger.error("Phidget Exception %i: %s" % (e.code, e.details))
            try:
                self.interfaceKit.closePhidget()
            except PhidgetException as e:
                self.logger.error("Phidget Exception %i: %s" % (e.code, e.details))
            raise e
            
        return True
    
    def disconnect(self):
        try:
            self.interfaceKit.closePhidget()
        except PhidgetException as e:
            self.logger.error("Phidget Exception %i: %s" % (e.code, e.details))
            raise e