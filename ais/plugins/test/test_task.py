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
from ais.ui.models import Config
from wtforms import Form, StringField, HiddenField, FormField, FieldList
from flask.ext.admin import expose
import logging, datetime

logger = logging.getLogger(__name__)



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
        logger.info(self._print_keyword_args("Test_Task Run called", **kwargs)) 
    
    def configure(self, **kwargs):
        logger.debug(self._print_keyword_args("Init called", **kwargs)) 
        self.initialized = True
          
    def __init__(self, **kwargs):
        Task.__init__(self,**kwargs)
        self.widgetized = True
        self.viewable = True
        logger.debug(self._print_keyword_args("Init called", **kwargs)) 
        
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

        if h.is_form_submitted():
            form_data = request.form
            form_type = form_data.get('id')
            if form_type == 'init':
                flash("Init Form submitted")
            elif form_type == 'run':
                flash("Run Form Submitted")
                
        #load init config stored
        icfg = Config.query.filter_by(plugin=self.name, role="Initalize").first()
        init_form = InitArgsForm(id="init",name=icfg.name, arga = icfg.args.get('arg1'), argb =icfg.args.get('arg2'))
        
        run_form = RunArgsForm(id="run")
        
        ##render page 
        return self.render(
            self.view_template, 
            init_form = init_form, 
            return_url = "/test_task/",
            run_form=run_form
            )