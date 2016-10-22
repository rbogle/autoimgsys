# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#R
#   <author> Rian Bogle </author>

import ais.plugins.sync.utility as utility
from ais.ui.models import Config,Plugin
from ais.ui import db
from flask.ext.admin.form import BaseForm
from wtforms import HiddenField,StringField
from sqlalchemy.exc import SQLAlchemyError
from flask.ext.admin import expose
from flask import jsonify
import copy

   
class SyncForm(BaseForm):
    id = HiddenField()
    cid = HiddenField()
    name = StringField("Name", description="Name for this sync config")
    src = StringField("Source", description="Source Directory for this sync config")
    dst = StringField("Destination", description="Destination for this sync config")
    excl = StringField("Excludes", description="Comma separated name Patterns to exlude from sync")
    opts = StringField("Opts", description="Other Rsync options for this sync config")
    
class Sync(utility.Utility):
           
    def __init__(self, **kwargs):
        super(Sync,self).__init__(**kwargs) 
        self.widgetized = True
        self.viewable = True
        self.enabled = True
 
    def configure(self, **kargs):
        if kargs.get('sync_enabled', False):
            self.start_rtsync() 

    def get_configs(self):
        init = Config(
            name ="Data Sync", 
            role="Initalize",
            args={'sync_enabled': False}
        )
        cfg = Config(
            name ="Backup of Data", 
            role="Runtime",
            args={
                'src': '/mnt/data/',
                'dst': '/mnt/backup',
                'excl': '',
                'opts': '',
                'mkrt': False
            }
        )
        return [init, cfg]
           
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
        f.dst.data = c.args.get('dst', '') 
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
 
 #  Method edits or adds a runtime config object for the data sync plugin
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
        c.args['dst'] = form_data['dst']
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
        
 # Method takes form data and changes config objects arg property with a mkrt field. 
    def _make_realtime(self, form_data):
        self.logger.debug(form_data)
        id = int(form_data['conf_id'])
        c = Config.query.get(id)
        if c is None:
            return False;
        new_args = copy.deepcopy(c.args)
        if form_data.get('enabled', False):       
            new_args['mkrt'] = True
            self.add_watch(new_args)
        else:
            new_args['mkrt'] = False
            self.remove_watch(new_args)
        c.args = new_args
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(e.message)
            return False    
        return True

    def _do_rsync(self, form_data):
        src = form_data.get('src', "")
        dst = form_data.get('dst', "")
        
    def set_rtsync(self, state):
        if state in ['False', 'false', 0]: 
            state = False
        else:
            state = True
        self.logger.debug("set_rtsync got: %s" %state)
#        if bool(state) != bool(self.get_rtsync()):
        if bool(state):
            self.logger.debug("starting rtsync")
            self.save_rtsync_state(True)
            self.start_rtsync()
        else:
            self.logger.debug("stoping rtsync")
            self.save_rtsync_state(False)                
            self.stop_rtsync()
  
    def save_rtsync_state(self, state):
        init = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
        if init is None:
            init = Config(name = "Data Sync")             
            init.plugin = Plugin.query.filter(Plugin.name==self.name).first()
            init.role = "Initialize"
            init.args = dict()
            init.args['sync_enabled'] = bool(state)
            db.session.add(init)
        else:
            new_args = copy.deepcopy(init.args)
            new_args['sync_enabled'] = bool(state)
            init.args = new_args
#             init.args['sync_enabled'] = bool(state)
        db.session.commit()

    def get_status(self):
#       alert = {
#        'cat': 'info',
#         'txt': 'All is well'
#        }
#       self.statusq.append(alert) 
       alerts = copy.deepcopy(self.statusq)
       self.statusq =list()
       return jsonify(alerts=alerts)
       
    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request

        modal = request.args.get('modal', None)
        active_tab = request.args.get('tab', 'otime')
        args = request.args
        rt_enabled = self.get_rtsync()
        #some form submitted
        if h.is_form_submitted():
            form_data = request.form
            form_type = form_data.get('id')        
            self.logger.debug("form is: %s" %form_type)
            if form_type == "status":
                return self.get_status()                
            if form_type =="rsync":
                active_tab = "otime"
                self._do_rsync(form_data)
            if form_type == "mkrt":
                active_tab = "rtime"
                self._make_realtime(form_data) 
            if form_type == "rtsync":
                active_tab = "rtime"
                self.set_rtsync(form_data.get('enable'))
                rt_enabled = self.get_rtsync()
            if form_type == "edit":
                active_tab = "sched"
                if self._edit_config(form_data):
                    flash("Sync config updated", category="message")
                else:
                    flash("Sync could not be updated", category="error")                    
            if form_type == "delete":
                active_tab = "sched"
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
            ('otime', self.path+"/otime_panel.html","One-Time Synchronization"),
            ('sched',self.path+"/sched_panel.html","Data Sync Configuration"),
            ('rtime',self.path+"/rtime_panel.html","Real-Time Synchronization")
        ]
        
        ##render page 
        return self.render(
            self.view_template, 
            panels = p,
            syncs = sync_configs,
            running = rt_enabled,
            active_tab = active_tab,
            return_url = self.url
            )