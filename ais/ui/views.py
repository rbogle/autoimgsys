from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.base import *
from flask import Markup
from wtforms.fields import  TextAreaField
from ais.ui import flask
from ais.ui.models import *

import logging, ast
logger = logging.getLogger(__name__)
 
class DashboardView(AdminIndexView):
    '''
        DashboardView maintains a list of plugins who wish to 
        output info to the dashboard in a widget block
        each plugin should mark themselves as viewable
        and implement the render_view method to return html content. 
    '''
    def __init__(self, name=None, category=None, endpoint=None, url=None, template='admin/index.html'):
        super(DashboardView, self).__init__(name, category, endpoint, url, template)
        self.plugins = list()
        
    def register_plugin(self, plugin):
        self.plugins.append(plugin)
 
    def get_plugins_widgets(self):
        widgets = list()
        if self.plugins:
            for p in self.plugins:
                widgets.append(Markup(p.widget_view()))
        return widgets
 
    @expose('/')
    def index(self):
        return self.render('ui/templates/index.html', widgets=self.get_plugins_widgets())
        
class ConfigurableView(ModelView):
    '''
        Configurable View is used for those models that have a pickletype field
        called args. We safely eval the form input to convert string to dict
        and rename the args field to Config.
    '''
    def on_model_change(self, form, model, is_created):
        model.args = ast.literal_eval(model.args)
        return model

    form_extra_fields = {
        'args': TextAreaField("Config")
    }

class AuditorView(ModelView):
    pass

class JobView(ModelView):
    '''
        JobView customized the edit and create forms 
        and performs callbacks to aisapp to sync enabled jobs in the db
        with scheduled jobs in the scheduler. 
    '''

    form_create_rules = ('name', 'schedule', 'action', 'enabled')
    form_edit_rules = ('name', 'schedule', 'action', 'enabled')
    
    def update_model(self, form, model):
        logger.debug("ScheduleView on_model_change called")
        success = super(JobView, self).update_model(form,model)
        if success:
            flask.aisapp.schedule_jobs_from_db()  
            return True
        return False    
    
    def create_model(self, form):
        logger.debug("ScheduleView on_model_change called")
        success = super(JobView, self).create_model(form)
        if success:
            flask.aisapp.schedule_jobs_from_db()  
            return True
        return False
        
    def delete_model(self, model):
        logger.debug("ScheduleView delete_model called")
        success = super(JobView, self).delete_model(model)
        if success:
            flask.aisapp.schedule_jobs_from_db()
            return True
        return False
            