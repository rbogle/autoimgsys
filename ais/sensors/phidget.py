# -*- coding: utf-8 -*-

from relay import Relay
import logging
from Phidgets.PhidgetException import PhidgetException
from Phidgets.Devices.InterfaceKit import InterfaceKit

class Phidget(Relay):

        
    def set_port(self, port, state):
        if self.connect():
            try:
                self.interfaceKit.setOutputState(port, state)
            except PhidgetException as e:
                logging.error("Phidget Exception %i: %s" % (e.code, e.details))
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
            logging.error("Runtime error: %s" % e.message)
            return False
            
        except PhidgetException as e:
            logging.error("Phidget Exception %i: %s" % (e.code, e.details))
            try:
                self.interfaceKit.closePhidget()
            except PhidgetException as e:
                logging.error("Phidget Exception %i: %s" % (e.code, e.details))
            return False
            
        return True
    
    def disconnect(self):
        try:
            self.interfaceKit.closePhidget()
        except PhidgetException as e:
            logging.error("Phidget Exception %i: %s" % (e.code, e.details))
    