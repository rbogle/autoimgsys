# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from ais.lib.task import Task

class System(Task):
    
    def __init__(self, **kwargs):
        super(System, self).__init__(**kwargs)
        self.enabled = True
        self.viewable = True
        self.widgetized = True
        self.use_filestore = True
        self.use_sqllog = True
        self.view_template = self.path+'/system.html'
        self.widget_template = self.path+'/sys_widget.html'

    def run(self, **kwargs):
        pass
    
    @expose('/')
    @expose('/<action>')
    def plugin_view(self, action=None):
        
        w = (
            ('Function A', 'A content', 'A action'),
            ('Function B', 'B content', 'B action'),
            ('Function C', 'C content', 'C action'),
            ('Function D', 'D content', 'D action')
        )        
        return self.render(self.view_template, widgets=w)