from plugin import PluginObj

class Auditor(PluginObj):
    
    def respond(self, event):
        """ Called when object registered as an apscheduler event listener
        """
        raise NotImplementedError