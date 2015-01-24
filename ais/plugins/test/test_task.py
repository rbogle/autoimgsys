# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>

from ais.lib.task import Task
from ais.ui.models import Config,Plugin
from wtforms import Form, StringField, HiddenField, TextAreaField
from flask.ext.admin import expose
import datetime, ast
   
class RunArgsForm(Form):
    id = HiddenField()
    name = StringField("Set Name")
    arg1 = StringField('Arg 1')
    arg2 = StringField('Arg 2')
    
class InitArgsForm(Form):
    id = HiddenField()
    arg1 = StringField('Arg 1')
    arg2 = StringField('Arg 2')
    
class Test_Task(Task):
    
    def run(self, **kwargs):     
        self.last_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')	              
        self.logger.info(self._print_keyword_args("Test_Task Run called", **kwargs)) 
        import random
        if random.random()>.5:
            raise Exception("Ugh We Failed our Task")
        else:
            return "Test Task run is happy as a clam!"
    
    def configure(self, **kwargs):
        self.logger.debug(self._print_keyword_args("Init called", **kwargs)) 
        self.initialized = True
          
    def __init__(self, **kwargs):
        super(Test_Task,self).__init__(**kwargs) 
        self.widgetized = True
        self.viewable = True
        self.logger.debug(self._print_keyword_args("Init called", **kwargs)) 
        
    def _print_keyword_args(self, msg, **kwargs):
        # kwargs is a dict of the keyword args passed to the function
        str= msg+'\n'
        for key, value in kwargs.iteritems():
            str+= "%s = %s\n" % (key, value)  
        return str

    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request
        active_tab = 'main'
        if h.is_form_submitted():
            form_data = request.form
            form_type = form_data.get('id')
            if form_type == 'init':
                #load init config stored
                icfg = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
                if icfg is None:
                    plg = Plugin.query.filter_by(name=self.name).first()
                    icfg = Config(plugin=plg, role="Initalize", args={}, name="Test_Task Init")
                #update config obj with formdata
                new_args = icfg.args.copy()

                #icfg.args = new_ar
                new_args['arg1']= form_data.get('arg1') #this one is a string
                new_args['arg2']= form_data.get('arg2') #this one should be a dict
                icfg.args = new_args
                try:
                    self.app.db.session.add(icfg)
                    self.app.db.session.commit()
                except:
                    flash("Init form submission failed, bad data in form", "danger")
                    active_tab = 'init'
                else:    
                    flash("Init Form submitted", "message")
                    
            elif form_type == 'run':
                #load init config stored
                plg = Plugin.query.filter_by(name=self.name).first()
                icfg = Config(
                    name=form_data.get('name'), 
                    role="Runtime",
                    plugin=plg
                )
                #update config obj with formdata
                icfg.args = dict()
                icfg.args['arg1']=form_data.get('arg1')
                icfg.args['arg2']=form_data.get('arg2')
                try:
                    self.app.db.session.add(icfg)
                    self.app.db.session.commit()
                except ValueError:
                    flash("Run form submission failed, bad data in arg2", "danger")
                    active_tab = 'run'
                except:
                    flash("Run form submission failed", "danger")
                    active_tab = 'run'
                else:    
                    flash("Run Form submitted", "message")
                
        #load init config stored
        icfg = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
        if icfg is None:
            plg = Plugin.query.filter_by(name=self.name).first()
            icfg = Config(plugin=plg, role="Initalize", args={}, name="Test_Task Init")
            
        init_form = InitArgsForm(id="init",name=icfg.name, arg1 = icfg.args.get('arg1', ""), arg2 =icfg.args.get('arg2', ""))
        
        run_form = RunArgsForm(id="run")
        
        ##render page 
        return self.render(
            self.view_template, 
            init_form = init_form, 
            active_tab = active_tab,
            return_url = "/test_task/",
            run_form=run_form
            )