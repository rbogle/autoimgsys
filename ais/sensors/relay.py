# -*- coding: utf-8 -*-

class Relay(object):
    
    
    def set_port(self, port, state):
        raise NotImplementedError

    def get_port(self, port, state):
        raise NotImplementedError

    