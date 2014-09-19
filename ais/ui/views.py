from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.base import *
from wtforms.fields import  TextAreaField
import logging
 
class DashboardView(AdminIndexView):
    
    def register_plugins(self, pluginlist):
        self.plugins = pluginlist
 
    def get_plugin_widgets(self):
        return self.plugins
 
    @expose('/')
    def index(self):
        arg1 = self.get_plugin_widgets()
        return self.render('ui/templates/index.html', widgets=arg1)
        
class ConfigurableView(ModelView):

    form_extra_fields = {
        'args': TextAreaField("Config")
    }

