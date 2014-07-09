from pprint import pprint

class Task:

    def __init__(self, name, **kwargs):
        self.name = name
        vars(self).update(kwargs)
    
    def run(self, **kwargs):
        raise NotImplementedError
        
    def respond(self, event):
        raise NotImplementedError
    
    def diag(self):
        pprint(self.__dict__)
    