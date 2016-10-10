# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#R
#   <author> Rian Bogle </author>

from ais.lib.task import Task
from ais.ui.models import Config,Plugin
#from wtforms import Form, StringField, HiddenField
from flask.ext.admin import expose
import datetime
   
    
class Sync(Task):
           
    def __init__(self, **kwargs):
        super(Sync,self).__init__(**kwargs) 
        self.widgetized = True
        self.viewable = True
        self.enabled = True
        
    def run(self, **kwargs):     
        self.last_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')	              
        self.logger.info(self._print_keyword_args("Test_Task Run called", **kwargs)) 

    def get_widget_modal(self, name, kwargs):
        if name == 'edit':
            return self.get_edit_modal(kwargs)
        if name == 'delete':
            return self.get_delete_modal(kwargs)
 
        
    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request

        modal = request.args.get('modal', None)
        active_tab = request.args.get('active_tab', 'sched')
        args = request.args
        
        #some form submitted
        if h.is_form_submitted():
            form_data = request.form
            form_type = form_data.get('id')        
            self.logger.debug("form is: %i" %form_type)
        # we're cycling through a modal dialog via ajax/json
        if modal is not None:
            return self.get_widget_modal(modal, args)    
            
        #load init config stored
        sync_configs = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Runtime").all()
        

        p = [
            ('sched',self.path+"/sched_panel.html","Scheduled Syncs"),
            ('rtime',self.path+"/rtime_panel.html","Realtime Syncs")
        ]
        
        ##render page 
        return self.render(
            self.view_template, 
            panels = p,
            syncs = sync_configs,
            active_tab = active_tab,
            return_url = self.url
            )