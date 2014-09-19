from plugin import Plugin

class Relay(Plugin):
    
    def set_port(self, port, state):
        raise NotImplementedError

    def get_port(self, port, state):
        raise NotImplementedError

    