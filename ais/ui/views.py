from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.sqla.filters import BooleanEqualFilter
from flask.ext.admin.base import *
from sqlalchemy import func
from flask import Markup,redirect,flash,jsonify
from wtforms.fields import  TextAreaField, SelectMultipleField


from ais.ui import flask,db
from ais.ui.models import *
from ais.lib.listener import Listener

import logging, ast, datetime
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
 
    def get_plugin_widgets(self):
        widgets = list()
        if self.plugins:
            for p in self.plugins:
                if p.enabled:
                    url= (p.url if p.viewable else None)
                    widgets.append((p.name, Markup(p.widget_view()), url))
        return widgets
        
    @expose('/')
    @expose('/<action>')
    def index(self,action=None):
        now = datetime.datetime.now().strftime("%a, %b %d. %Y %H:%M")        
        if action=='resume':
            flask.aisapp.resume()
        elif action=='pause':
            flask.aisapp.pause()
        elif action=='time':
            return jsonify(time=now)
        elif action=='widgets':
            return jsonify(widgets=self.get_plugin_widgets())
        elif action is not None:
            return redirect('/')

        status,jobs,msg = flask.aisapp.get_status()
        w = self.get_plugin_widgets()
        return self.render('admin/index.html', 
                          server_status=status, server_status_msg=msg, 
                          jobs_scheduled=jobs, widgets=w, time=now)
                          
class EventView(ModelView):
    can_edit = False
    can_create = False
    can_delete = False
    column_searchable_list=('msg', 'trace')
    column_filters = ('datetime', 'plugin','code', 'msg', 'trace')
    column_list =('datetime','plugin','code', 'msg', 'trace')                       
                          
class LogView(ModelView):
    can_edit = False
    can_create = False
    can_delete = False
    column_searchable_list=('level', 'logger', 'module', 'msg')
    column_filters = ('created', 'level','logger', 'module', 'msg')
    column_list =('created', 'level','logger', 'module', 'msg')                
        
class PluginView(ModelView):
    '''
        PluginView for Plugins allows Advanced user to disable enable plugins
        Disabled plugins will not be shown to Actions nor utilized in the dashboard
    '''

    can_create = False
    can_delete = False
    column_list =('name', 'category', 'class_name', 'enabled')
    
    #use overrides to filter down to just task plugins
    def get_query(self):
        return self.session.query(self.model).filter(self.model.category=="Task")
    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.category=="Task")
    
    def update_model(self, form, plugin):
        logger.debug("PluginView on_model_change called")
        success = super(PluginView, self).update_model(form, plugin)
        flask.aisapp.sync_plugin_status(plugin.name, plugin.enabled)
        if plugin.enabled and plugin.category=="Task": 
            flask.aisapp.initalize_plugin(plugin.name)
        return success  

def event_mask_formatter( view, context, model, event_mask):
    '''
        Function to evaluate event_masks and output a string equiv.
        used by AudtiorView below
    '''
    str_mask = ""
    evt_mask = model.event_mask
    for name,bit_mask in Listener.event_types.iteritems():
        if (bit_mask & evt_mask) != 0:
            if str_mask=="":
                str_mask += name
            else:
                str_mask += " | " + name
    return str_mask
        
class AuditorView(ModelView):
    '''
        AuditorView customizes the edit and create forms 
        and performs callbacks to aisapp to sync enabled jobs in the db
        with scheduled jobs in the scheduler. Performs event_mask formatting
        and conversion, and limits available plugins to Listeners.
    '''
    column_list = ('name', 'event_mask', 'plugin', 'enabled')
    column_formatters = dict( event_mask=event_mask_formatter )
    form_create_rules = ('name', 'event_mask', 'plugin', 'enabled')
    form_edit_rules = ('name', 'event_mask', 'plugin', 'enabled')
    form_overrides = dict(event_mask=SelectMultipleField)
    form_args = dict (
        event_mask = dict(
            choices = [
                (128, 'EVENT_JOB_ADDED'),
                (256, 'EVENT_JOB_REMOVED'),
                (512, 'EVENT_JOB_MODIFIED'),
                (1024, 'EVENT_JOB_EXECUTED'),
                (2048, 'EVENT_JOB_ERROR'),
                (4096, 'EVENT_JOB_MISSED')         
            ],
            coerce = int
       ),
       plugin = dict( # filter the select list down to just listener plugins
           query_factory= lambda: db.session.query(Plugin).filter_by(category="Listener"),
           allow_blank = False
       )
   )
    
      
    def update_model(self, form, model):
        logger.debug("AuditorView on_model_change called")
        
        #parse multiselect data and OR it for full mask value
        evts = form.event_mask.data
       # logger.debug("AuditorVew form got: %s" %(form.event_mask.data))
        mask=0
        for evt in evts:
           # logger.debug("AuditorVew- evt:%s mask:%s" %(evt, mask))
            mask |=evt
        form.event_mask.data = mask
        logger.debug("AuditorVew form sent: %s" %(form.event_mask.data))
        
        success = super(AuditorView, self).update_model(form,model)
        flask.aisapp.register_listeners_from_db()  
        return success    
    
    def create_model(self, form):
        logger.debug("AuditorView on_model_change called")
        #parse multiselect data and or it for full mask value
        evts = form.event_mask.data
        #logger.debug("AuditorVew form got: %s" %(form.event_mask.data))
        mask=0
        for evt in evts:
            mask |= evt
        form.event_mask.data = mask
        #logger.debug("AuditorVew form sent: %s" %(form.event_mask.data))
        success = super(AuditorView, self).create_model(form)
        flask.aisapp.register_listeners_from_db()  
        return success  
        
    def delete_model(self, model):
        logger.debug("AuditorView delete_model called")
        success = super(AuditorView, self).delete_model(model)
        flask.aisapp.register_listeners_from_db()  
        return success  

class JobView(ModelView):
    '''
        JobView customized the edit and create forms 
        and performs callbacks to aisapp to sync enabled jobs in the db
        with scheduled jobs in the scheduler. 
    '''
    column_list = ('name', 'schedule', 'config', 'enabled', 'running')
    form_create_rules = ('name', 'schedule', 'config', 'enabled')
    form_edit_rules = ('name', 'schedule', 'config', 'enabled')

    form_args = dict (
       config = dict( #filter down select list to just Task plugins
           query_factory= lambda: db.session.query(Config).filter_by(role="Runtime"),
           allow_blank = False
       ) 
    )
    
    def update_model(self, form, model):
        logger.debug("ScheduleView on_model_change called")
        flask.aisapp.unschedule_job(model)
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
        flask.aisapp.unschedule_job(model)
        success = super(JobView, self).delete_model(model)
        if success:
            flask.aisapp.schedule_jobs_from_db()
            return True
        return False
    
   
class ConfigView(ModelView):
    '''
        ConfigView is used for Config model, has functionality to validate
        pickletype field called args. We safely eval the form input to 
        convert string to dict and rename the args field to Config.
    '''    
    column_list = ('name', 'plugin', 'role' , 'args')
    form_create_rules = ('name', 'plugin', 'role' , 'args')
    form_edit_rules = ('name', 'plugin', 'role' , 'args')    
    
    def on_model_change(self, form, model, is_created):
        '''
            called before transaction committed to db 
        '''
        if model.args != "":
            try:
                model.args = ast.literal_eval(model.args)
            except ValueError:
                flash("Args must be a Python Type: Quoted String, list, dict, tuple, number", 'error')
                model.args = ""
        return model
        
    #form_overrides = dict(plugin=SelectField)
    form_extra_fields = {
        'args': TextAreaField("Config")
    }
     
    form_args = dict (
       plugin = dict( #filter down select list to just Task plugins
           query_factory= lambda: db.session.query(Plugin).filter_by(category="Task", enabled=True),
           allow_blank = False
       ) 
    )
