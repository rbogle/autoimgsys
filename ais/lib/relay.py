from plugin import PluginObj

class Relay(PluginObj):
    
    def set_port(self, port, state):
        raise NotImplementedError

    def get_port(self, port, state):
        raise NotImplementedError

    