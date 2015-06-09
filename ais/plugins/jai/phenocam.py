import ais.plugins.jai.jai as jai #inhertiance path due to Yapsy detection rules
from ais.ui.models import Config, Plugin, Log
from wtforms import Form,StringField,HiddenField,TextAreaField, BooleanField,IntegerField,validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask.ext.admin import expose
import ast,time
from collections import OrderedDict

#logger = logging.getlogger("PhenoCam")

class RunConfigListForm(Form):
    id = HiddenField()
    config = QuerySelectField("Stored Configs:", allow_blank=True, blank_text="Create New", 
                          query_factory=lambda: Config.query.join(Plugin).filter(Plugin.name=="PhenoCam").filter(Config.role=="Runtime").all()                          
                          )    
                          
class RunArgsForm(Form):
    id = HiddenField()
    name = StringField("Config Name")
    args = TextAreaField('Run Config')
    
class InitArgsForm(Form):
    id = HiddenField()
    rgb = StringField('RGB Sensor Mac Address')
    nir = StringField('NIR Sensor Mac Address')
    use_relay = BooleanField("Use Power Control?")
    relay_name = QuerySelectField("Relay Plugin", query_factory= lambda: Plugin.query.filter_by(category='Relay').all())
    relay_port = IntegerField("Relay Port")
    relay_delay = IntegerField("Seconds to Delay")
 
class TestParamsForm(Form):
    id = HiddenField()
    exposure = IntegerField("Exposure 20-33333 uS", default=15000, validators=[validators.NumberRange(min=20, max=33333)])
    gain = IntegerField("Gain -89 to 593", default=0, validators=[validators.NumberRange(min=-89, max=593)])    


class PhenoCam(jai.JAI_AD80GE): #note inheritance path due to Yapsy detection rules
    
    def __init__(self,**kwargs):
        """Initializes camera instance
        
           Args:
               **kwargs Named arguments to configure the camera(s)
                   Sensors: dict of name: mac address for each of the sensors on board
        """
        super(PhenoCam,self).__init__(**kwargs) 
        self.viewable = True
        self.widgetized = True
        self.view_template = self.path+'/phenocam.html'
        self.widget_template = self.path+'/pheno_widget.html'
        self.use_filestore = True
        self.use_sqllog = True
        self.last_run={}
        self.last_run['success'] = False
        self.last_run['error_msg'] = "No runs attempted"

        
    def update_init_model(self, form):
        from flask import flash
        #load init config stored
        icfg = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
        if icfg is None:
            plg = Plugin.query.filter_by(name=self.name).first()
            icfg = Config(plugin=plg, role="Initalize", args={}, name="PhenoCam Init")
        #update config obj with formdata
        new_args = icfg.args.copy()
        new_args['sensors']=(
            {"name": "rgb", "mac": form.get('rgb')},
            {"name": "nir", "mac": form.get('nir')}        
        ) 
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
        
        icfg = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
        if icfg is None:
            plg = Plugin.query.filter_by(name=self.name).first()
            icfg = Config(plugin=plg, role="Initalize", args={}, name="PhenoCam Init")
#        form  = InitArgsForm(id="init")
        sensors={}
        sl = icfg.args.get("sensors", None)
        if sl is not None:
            for s in sl:
                sensors[s.get('name')]=s.get('mac')
        
        form = InitArgsForm(id='init', rgb=sensors.get('rgb', ""), nir=sensors.get('nir',"") )
        
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
                icfg = Config(plugin_id=plg.id, role="Runtime", name=form.get('name'))
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
                kwargs['file_prefix']="PhenoCam_Test"
                kwargs['image_type'] = 'jpg'
                kwargs['pixel_formats']=(
                    {'pixel_format': 'BayerRG8', 'sensor': 'rgb'}, 
                    {'pixel_format': 'Mono8', 'sensor': 'nir'}
                )
                kwargs['exposure_time'] = form.exposure.data
                kwargs['gain']= form.gain.data
                kwargs['persist']=True
                try:
                    self.run(**kwargs)
                    ts = int(time.time())
                    content = Markup("<img id='rgb' src='/fileadmin/download/PhenoCam/test/PhenoCam_Test_rgb.jpg?")
                    content += Markup(str(ts))
                    content += Markup("' /><br/>")
                    content += Markup("<img id='nir' src='/fileadmin/download/PhenoCam/test/PhenoCam_Test_nir.jpg?")
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
        icfg = Config.query.join(Plugin).filter(Plugin.name==self.name).filter(Config.role=="Initalize").first()
        if icfg is not None:
            kwargs = icfg.args.copy()
            self.configure(**kwargs)
            flash("Initialization Completed")
        else:
            flash("Camera Settings need to be set")
        return redirect('/phenocam')
        
    def do_status(self):
        from flask import Markup
        content = Markup("<div class='panel panel-default'>")
        info = self.status()
        err = info.get('Error', None)
        rgb = info.get('rgb', None)        
        nir = info.get('nir', None)   
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
            table['header']="<thead><tr><th>&nbsp</th><th>RGB</th><th>NIR</th></tr></thead>"
            table['tbodyo']='<tbody>'
            for sens in (rgb,nir):
                for k,v in sens.iteritems():
                    if k not in table.keys():
                        table[k]="<tr><td>%s</td><td>%s</td>" %(k,v)
                    else:
                        table[k]+="<td>%s</td></tr>" %str(v)
            table['tbodyc']="</tbody>"
            table['tablec']="</table>"
            for k,v in table.iteritems():
                content+=Markup(v+'\n')
            
        content+=Markup("</div>")
        return content
    
    def get_logs(self, rargs):
        from flask import jsonify
        last = rargs.get("last", -1)
        logs = Log.query.filter(Log.logger==self.name, Log.id>int(last)) \
            .order_by(Log.created.desc()).limit(200).all()
        #TODO:logs could be None what happens
        if logs is not None:
            data = OrderedDict()
            for log in reversed(logs):
                data[log.id]={'msg':log.msg, 'level':log.level, 
                    'datetime':log.created, 'module':log.module}
        return jsonify(logs=data)
    
    def get_configs(self):
        cfg = Config(
            name ="HDR 10 Shot", 
            role="Runtime",
            args={
                        'pixel_formats':(
                            {'sensor':'rgb', 'pixel_format': 'BayerRG8'},
                            {'sensor':'nir', 'pixel_format': 'Mono8'}        
                        ),
                        'file_prefix': 'hdr',
                        'sequence':[
                            {'exposure_time': 20},
                            {'exposure_time': 40},
                            {'exposure_time': 120},
                            {'exposure_time': 240},
                            {'exposure_time': 480},
                            {'exposure_time': 960},
                            {'exposure_time': 1920},
                            {'exposure_time': 3840},
                            {'exposure_time': 7680},
                            {'exposure_time': 15360},
                            {'exposure_time': 30720},
                        ]       
                    }
        )
        return [cfg]
       
      
    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request
        
        if not self.initalized:
            flash("PhenoCam has not been properly initalized! See Settings Tab", 'error' )
        d = self._powerdelay   
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
            status['msg'] = "PhenoCam initalized and ready"
        else:
            status['msg'] = "PhenoCam needs initialization"
        ##render page 
        return self.render(
            self.view_template, status=status,
            init_form = init_form, 
            active_tab = active_tab,
            return_url = "/phenocam/",
            run_list=run_list,
            list_opts = list_opts,
            run_form=run_form,
            delay=d
            )