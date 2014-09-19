from plugin import Plugin

class Auditor(Plugin):
    
    def respond(self, event):
        """ Called when object registered as an apscheduler event listener
        """
        raise NotImplementedError