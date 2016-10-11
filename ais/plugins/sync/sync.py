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
from ais.ui import db
from flask.ext.admin.form import BaseForm
from wtforms import HiddenField,StringField
from sqlalchemy.exc import SQLAlchemyError
from flask.ext.admin import expose
from flask import jsonify
import datetime
   
class SyncForm(BaseForm):
    id = HiddenField()
    cid = HiddenField()
    name = StringField("Name", description="Name for this sync config")
    src = StringField("Source", description="Source Directory for this sync config")
    dest = StringField("Destination", description="Destination for this sync config")
    excl = StringField("Excludes", description="Comma separated name Patterns to exlude from sync")
    opts = StringField("Opts", description="Other Rsync options for this sync config")
    
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

    def get_edit_modal(self, kwargs):
        title = "Edit Data Sync Config"
        f = SyncForm(id="edit")
        id = kwargs.get('conf_id', '')
        if id is not u'':
            c = Config.query.get(int(id))
        else: 
            c = Config(name="")
            c.args = dict()
        f.name.data = c.name
        f.cid.data = c.id
        f.src.data = c.args.get('src', '') 
        f.dest.data = c.args.get('dest', '') 
        f.excl.data = c.args.get('excl', '')
        f.opts.data = c.args.get('opts', '')
        body=self.render(self.path+"/modal_form.html", aform=f)
        return jsonify({'title':title, 'body':body, 'url':""})      
        
    def _delete_config(self, form_data):
        id = int(form_data['conf_id'])
        c = Config.query.get(id)
        if c is None:
            return False;
        try:
            db.session.delete(c)
            db.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(e.message)
            return False    
        return True   
 
    def _edit_config(self, form_data):
        if form_data['cid'] is not u'':
            c = Config.query.get(int(form_data['cid']))
            c.name = str(form_data['name'])
        else: #adding new config
            c = Config(name = form_data['name'])             
            c.plugin = Plugin.query.filter(Plugin.name == self.name).first()
            c.role = "Runtime"
            
        c.args = dict()
        c.args['src'] = form_data['src']
        c.args['dest'] = form_data['dest']
        c.args['excl'] = form_data['excl']
        c.args['opts'] = form_data['opts']
        #commit it.     
        try:        
            if c.id is None:
                db.session.add(c) 
            db.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(e.message)
            return False
        return True
            
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
            self.logger.debug("form is: %s" %form_type)
            if form_type == "edit":
                if self._edit_config(form_data):
                    flash("Sync config updated", category="message")
                else:
                    flash("Sync could not be updated", category="error")                    
            if form_type == "delete":
                if self._delete_config(form_data):
                    flash("Sync Removed!", category="message")
                else:
                    flash("Sync could not be removed", category="error")
                
        # we're cycling through a modal dialog via ajax/json
        if modal is not None:
            return self.get_widget_modal(modal, args)    
            
        #load init config stored
        sync_configs = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Runtime").all()
        

        p = [
            ('sched',self.path+"/sched_panel.html","Data Sync Configuration"),
            ('rtime',self.path+"/rtime_panel.html","Real-Time Synchronization")
        ]
        
        ##render page 
        return self.render(
            self.view_template, 
            panels = p,
            syncs = sync_configs,
            active_tab = active_tab,
            return_url = self.url
            )