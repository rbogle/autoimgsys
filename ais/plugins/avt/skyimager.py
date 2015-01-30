# -*- coding: utf-8 -*-

import ais.plugins.avt.avt as avt #inhertiancew path due to Yapsy detection rules
from ais.ui.models import Config, Plugin, Log
from wtforms import Form,StringField,HiddenField,TextAreaField, BooleanField,IntegerField,validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask.ext.admin import expose
from collections import OrderedDict
import time,ast

class RunConfigListForm(Form):
    id = HiddenField()
    config = QuerySelectField("Stored Configs:", allow_blank=True, blank_text="Create New", 
                          query_factory=lambda: Config.query.join(Plugin).filter(Plugin.name=="SkyImager").filter(Config.role=="Runtime").all()                        
                          )        
class RunArgsForm(Form):
    id = HiddenField()
    name = StringField("Config Name")
    args = TextAreaField('Run Config')
    
class InitArgsForm(Form):
    id = HiddenField()
    use_relay = BooleanField("Use Power Control?")
    relay_name = QuerySelectField("Relay Plugin", query_factory= lambda: Plugin.query.filter_by(category='Relay').all())
    relay_port = IntegerField("Relay Port")
    relay_delay = IntegerField("Seconds to Delay")
    
class TestParamsForm(Form):
    id = HiddenField()
    exposure = IntegerField("Exposure 21-153000000 uS", default=15000, validators=[validators.NumberRange(min=21, max=153000000)])
    gain = IntegerField("Gain 0-26db", default=0, validators=[validators.NumberRange(min=0, max=26)])    
    
class SkyImager(avt.AVT): #note inheritance path due to Yapsy detection rules
    
    def __init__(self,**kwargs):
        """Initializes camera instance
        
           Args:
               **kwargs Named arguments to configure the camera(s)
                   Sensors: dict of name: mac address for each of the sensors on board
        """
        super(SkyImager,self).__init__(**kwargs) 
        self.viewable = True
        self.widgetized = True
        self.use_filestore = True
        self.use_sqllog = True
        self.view_template = self.path+'/skyimager.html'
        self.widget_template = self.path+'/skyimg_widget.html'
        self.last_run={}
        self.last_run['success'] = False
        self.last_run['error_msg'] = "No runs attempted"
        

    def update_init_model(self, form):
        from flask import flash
        #load init config stored
        plg =Plugin.query.filter_by(name = self.name).first()
        icfg = Config.query.filter_by(plugin_id=plg.id, role="Initalize").first()
        if icfg is None:
            icfg = Config(plugin=plg, role="Initalize", args={}, name="SkyImager Init")
        #update config obj with formdata
        new_args = icfg.args.copy()

        # if using relay then add to args else remove from args
        if form.get('use_relay') =='y':
            plugin_name = Plugin.query.get(int(form.get('relay_name'))).name
            new_args['relay_name'] = plugin_name
            new_args['relay_port'] = int(form.get('relay_port'))
            new_args['relay_delay'] = int(form.get('relay_delay'))
        else:
            for arg in ('relay_name','relay_port','relay_delay' ):
                new_args.pop(arg, None)
                
        icfg.args = new_args
        try:
            self.app.db.session.add(icfg)
            self.app.db.session.commit()
        except:
            flash("Init form submission failed", "danger")
            return 'init'
        else: 
            self.configure(**icfg.args)
            flash("Camera Settings Updated, Initialization Completed", "message")
            return 'main'
            
    def update_init_form(self):
        #load init config stored
        plg =Plugin.query.filter_by(name = self.name).first()
        icfg = Config.query.filter_by(plugin_id=plg.id, role="Initalize").first()
        if icfg is None:
            icfg = Config(plugin=plg, role="Initalize", args={}, name="SkyImager Init")
        
        form = InitArgsForm(id='init')
        
        if 'relay_name' in icfg.args:
            form.use_relay.data = True
            form.relay_name.data = Plugin.query.filter_by(name=icfg.args.get("relay_name")).first()
            form.relay_delay.data = int( icfg.args.get("relay_delay", ""))
            form.relay_port.data = int(icfg.args.get("relay_port", ""))
        else:
            form.use_relay = False
        return form     
        
    def update_run_model(self,form):
        
        from flask import flash
        if form.get('name') != "":
            plg =Plugin.query.filter_by(name = self.name).first()
            icfg = Config.query.filter_by(plugin_id=plg.id, role="Runtime", name=form.get("name")).first()
            if icfg is None:
                icfg = Config(plugin=plg, role="Runtime", name=form.get('name'))
            #TODO we need to validate this as usable dict
            #update config obj with formdata
            new_args = form.get("args")
            icfg.args = ast.literal_eval(new_args)
            try:
                self.app.db.session.add(icfg)
                self.app.db.session.commit()
            except:
                flash("Run Config  submission failed", "error")
                return 'run'
            else: 
                flash("Run Config %s submitted" % form.get("name"), "message")
                return 'main'
        else:
            flash("You must submit name and args", "error")
            return 'run'
    
    def update_run_form(self, cfg_id=None):
        #display list or form
        if cfg_id is not None:
            icfg = Config.query.get(cfg_id)
            form = RunArgsForm(id="run", name = icfg.name, args=icfg.args)   
            return form
        else:
            return RunArgsForm(id="run")        
            
    def do_test(self, form=None, mode=None):
        from flask import Markup
        if mode=="stop": #we closed test dialog so power down.
            try:
                self.stop()
            except:
                pass
            return ""
        if form is None:
            form = TestParamsForm(id='test')
        else: 
            form = TestParamsForm(form)
            if form.validate():
                kwargs = {'sub_dir':'test', 'date_dir': None, 'date_pattern': None}
                kwargs['file_prefix']="SkyImager_Test"
                kwargs['image_type'] = 'jpg'
                kwargs['pixel_format']='BayerGB8'
                kwargs['exposure_time'] = form.exposure.data
                kwargs['gain']= form.gain.data
                kwargs['persist']=True
                try:
                    self.run(**kwargs)
                    ts = int(time.time())
                    content = Markup("<img src='/fileadmin/download/SkyImager/test/SkyImager_Test.jpg?")
                    content += Markup(str(ts))
                    content += Markup("' />")
                except:
                    content = Markup("Error")
                return content
            else:
                content=Markup("<ul class=errors>")
                for name,msgs in form.errors.iteritems():
                    for msg in msgs:
                        content+=Markup("<li>"+name+": ")
                        content+=Markup(msg)
                        content+=Markup("</li>")
                content+= Markup("</ul>")
                return content
        d=self._powerdelay
        return self.render(self.path+"/test.html", test_form = form, delay=d)
    
    def do_reinit(self):
        from flask import flash, redirect
        icfg =Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
        if icfg is not None:
            kwargs = icfg.args.copy()
            self.configure(**kwargs)
            flash("Initialization Completed")
        else:
            flash("Camera Settings need to be set")
        return redirect('/skyimager')
        
    def do_status(self):
        from flask import Markup
        content = Markup("<div class='panel panel-default'>")
        info = self.status()
        err = info.get('Error', None)  
        if err is not None: 
            content += Markup("<div class='panel-body'>")
            estr = "<strong> %s </strong><br/>" %err
            content += Markup(estr)
            traceback = info.get("Traceback", "No Trace Available")
            traceback = traceback.replace('\n', '<br />')
            content += Markup(traceback)
            content+=Markup("</div>")
        else:
            #build a pretty table from rgb, nir info
            table= OrderedDict()
            table['tableo']="<table class='table'>"
            table['header']="<thead><tr><th>&nbsp</th><th>Camera</th></tr></thead>"
            table['tbodyo']='<tbody>'

            for k,v in info.iteritems():
                table[k]="<tr><td>%s</td><td>%s</td></tr>" %(k,v)
            table['tbodyc']="</tbody>"
            table['tablec']="</table>"
            for k,v in table.iteritems():
                content+=Markup(v+'\n')
            
        content+=Markup("</div>")
        return content 

    def get_logs(self, rargs):
        from flask import jsonify
        last = rargs.get("last", -1)
        #TODO: should we limit # of returns
        logs = Log.query.filter(Log.logger==self.name, Log.id>int(last)).order_by(Log.created.desc()).limit(200).all()

        if logs is not None:
            data = OrderedDict()
            for log in reversed(logs):
                data[log.id]={'msg':log.msg, 'level':log.level, 
                    'datetime':log.created, 'module':log.module}
        return jsonify(logs=data)

    def get_configs(self):
       cfg = Config(
           name="HDR 10 Shot", 
           role="Runtime",
           args= {
            'file_prefix': 'hdr',
            'pixel_format': 'BayerGB8',
            'sequence':[
                {'exposure_time': 977},
                {'exposure_time': 1953},
                {'exposure_time': 3906},
                {'exposure_time': 7813},
                {'exposure_time': 15625},
                {'exposure_time': 31250},
                {'exposure_time': 62500},
                {'exposure_time': 125000},
                {'exposure_time': 250000},
                {'exposure_time': 500000},
                {'exposure_time': 1000000}
            ]      
            }
        )
       return [cfg]


    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request
        
        if not self.initalized:
            flash("SkyImager has not been properly initalized! See Settings Tab", 'error' )
        d=self._powerdelay    
        active_tab = 'main'
        #check for button actions on main
        run_cfg = None
        action = request.args.get('action')
        if action is not None:
            if action == "reinit":
                return self.do_reinit()
            if action == "test":
                return self.do_test(mode=request.args.get('mode'))   
            if action == "status":
                return self.do_status()
            if action == "logs":
                return self.get_logs(request.args)
                
        #check for form submit
        if h.is_form_submitted():
            form_data = request.form
            form_type = form_data.get('id')
            if form_type == 'init':
                active_tab = self.update_init_model(request.form)              
            elif form_type == 'run':
                active_tab = self.update_run_model(request.form)
            elif form_type == 'run_list':
                active_tab = 'run'
                #This gets the id of selected config
                if form_data.get('config')=='__None':
                    run_cfg=None
                else:
                    run_cfg = int(form_data.get('config'))
            elif form_type == 'test':
                return self.do_test(form=request.form)                
                
        #load init form           
        init_form = self.update_init_form()                
        
        #runconfiglistform lets us load saved configs for editing
        #not ajax just reload
        if run_cfg is not None:
            selected = Config.query.get(run_cfg)
        else:
            selected = None
        run_list = RunConfigListForm(id="run_list", config=selected)
        
        #this adds on change which reloads the form with data
        list_opts = {
                'widget_args':{
                    'config': {
                        'onchange': 'this.form.submit()'
                    }                
                }        
        }
        #now load run form with selected config or nothing.
        run_form = self.update_run_form(run_cfg)   
        
        status={}     
        status['ok'] = self.initalized
        if status['ok']:
            status['msg'] = "SkyImager initalized and ready"
        else:
            status['msg'] = "SkyImager needs initialization"
        ##render page 
        return self.render(
            self.view_template, status=status,
            init_form = init_form, 
            active_tab = active_tab,
            return_url = "/skyimager/",
            run_list=run_list,
            list_opts = list_opts,
            run_form=run_form,
            delay=d
            )
        