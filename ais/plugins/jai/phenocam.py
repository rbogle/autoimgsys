import ais.plugins.jai.jai as jai #inhertiance path due to Yapsy detection rules
from ais.ui.models import Config, Plugin, Log
from wtforms import Form,StringField,HiddenField,TextAreaField, BooleanField,IntegerField, SelectField, FormField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask.ext.admin import expose
import time
from collections import OrderedDict

#logger = logging.getlogger("PhenoCam")

class CapConfigListForm(Form):
    id = HiddenField()
    config = QuerySelectField("Stored Configs:", allow_blank=True, blank_text="Create New", 
                          query_factory=lambda: Config.query.join(Plugin).filter(Plugin.name=="PhenoCam").filter(Config.role=="Runtime").all()                          
                          )    
class InitArgsForm(Form):
    id = HiddenField()
    rgb = StringField('RGB Sensor Mac Address')
    nir = StringField('NIR Sensor Mac Address')
    use_relay = BooleanField("Use Power Control?")
    relay_name = QuerySelectField("Relay Plugin", query_factory= lambda: Plugin.query.filter_by(category='Relay').all())
    relay_port = IntegerField("Relay Port")
    relay_delay = IntegerField("Seconds to Delay")
 
class FileParamsForm(Form):
    id = HiddenField()
    sub_dir = StringField("Dir", description="Directory Name to Store Images under /Data/PhenoCam. Default is none.", filters=[lambda x: x or None])
    date_dir = SelectField("Grouping", description="How to group images in subfolders",choices=[('None','None'),('Yearly','Yearly'),('Yearly','Monthly'),('Daily','Daily'),('Hourly','Hourly')])
    date_dir_nested = BooleanField("Sort", default=False, description="Break out above grouping of images into nested subdirectories by date units")
    file_prefix = StringField("Prefix", description="Prepend text to filename for each image", filters=[lambda x: x or None])
    image_type = SelectField("Type", choices=[('jpg', 'JPG'), ('tif', 'TIFF')], description="Write images as file format")
    
class RGBParamsForm(Form):
    id = HiddenField()
    pixel_format = SelectField('Bits', description="Bit Depth for Image Capture",choices = [('BayerRG8','8-Bit'), ('BayerRG10','10-Bit'),('BayerRG12','12-Bit')])
    ob_mode = BooleanField("Mode", description="Use Optical Black Mode", default=False)

class NIRParamsForm(Form):
    id = HiddenField()
    pixel_format = SelectField('Bits', description="Bit Depth for Image Capture",choices = [('Mono8','8-Bit'), ('Mono10','10-Bit'), ('Mono12','12-Bit')] )
    ob_mode = BooleanField("Mode", description="Use Optical Black Mode", default=False)
    
class ShotParamsForm(Form):
    id = HiddenField()
    exposure = TextAreaField("Exposure", description="List of exposure values ranging from 0-33342 uS. one value per line", default="15000", validators=[validators.Regexp('\d*([\r\n]|$)',message="Only numbers on a single line")])
    gain = TextAreaField("Gain", default="0",description="List of gain values from -89 to 593, one value per line, a single value applies to all exposures", validators=[validators.Regexp('\d*([\r\n]|$)',message="Only numbers on a single line")])  

class CaptureParamsForm(Form):
    id = HiddenField()
    name = StringField("Config Name", description="Name for this capture configuration", validators=[validators.InputRequired()])
    file_settings = FormField(FileParamsForm)
    rgb_settings = FormField(RGBParamsForm)
    nir_settings = FormField(NIRParamsForm)
    shot_settings = FormField(ShotParamsForm)
    
class TestParamsForm(Form):
    id = HiddenField()
    exposure = IntegerField("Exposure 20-33333 uS", default=15000, validators=[validators.NumberRange(min=20, max=33333)])
    gain = IntegerField("Gain -89 to 593", default=0, validators=[validators.NumberRange(min=-89, max=593)])    
    obmode = BooleanField("OpticalBlack Mode", default=False)


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
    

# This will try to submit a config to the DB            
    def update_cap_model(self, data):
        from flask import flash
        form = CaptureParamsForm(data)
        action = data.get("submit")
        active_tab='main'
        cap_panel='file'
        if action =="Delete":
            plg = Plugin.query.filter_by(name = self.name).first()            
            icfg = Config.query.filter_by(plugin_id=plg.id, role="Runtime", name=data.get("name")).first()
            try:
                self.app.db.session.delete(icfg)
                self.app.db.session.commit()
            except: # bad delete return to cap
                flash("Could not delete config %s" % data.get('name'), "error")
                active_tab='cap'
            else: #good delete flash and return to main
                flash("Config %s has been deleted" % data.get('name'), "message")
                form=None
                active_tab='main'
        else:
            if form.validate():
                plg =Plugin.query.filter_by(name = self.name).first()            
                icfg = Config.query.filter_by(plugin_id=plg.id, role="Runtime", name=data.get("name")).first()
                if icfg is None:
                    icfg = Config(plugin_id=plg.id, role="Runtime", name=data.get('name'))
                icfg.args ={}
                icfg.args['sub_dir']=form.file_settings.sub_dir.data
                icfg.args['date_dir']=form.file_settings.date_dir.data
                icfg.args['date_dir_nested']=form.file_settings.date_dir_nested.data
                icfg.args['image_format'] =form.file_settings.image_type.data
                icfg.args['file_prefix']=form.file_settings.file_prefix.data
                icfg.args['rgb']={'pixel_format':form.rgb_settings.pixel_format.data,'ob_mode': form.rgb_settings.ob_mode.data }
                icfg.args['nir']={'pixel_format':form.nir_settings.pixel_format.data,'ob_mode': form.nir_settings.ob_mode.data }
                exp_vals = [ s.strip() for s in form.shot_settings.exposure.data.splitlines()]
                gain_vals = [ s.strip() for s in form.shot_settings.gain.data.splitlines()]
                icfg.args['sequence']=[]
                gains = len(gain_vals)          
                for e in exp_vals:
                    i = exp_vals.index(e)
                    gain=0; # default if nothing specified
                    if gains==1: # on val for all exposures
                        gain=gain_vals[0]
                    elif gains>1 and i < gains: #use whats specd
                        gain = gain_vals[i]   
                    icfg.args['sequence'].append ({'exposure_time': int(e), 'gain': int(gain) })
                try:
                    self.app.db.session.add(icfg)
                    self.app.db.session.commit()
                except: # failed submit return to cap with form as is
                    flash("Shot Config  submission failed", "error")
                    active_tab='cap'
                else: 
                    if action=="Submit":
                        #good submit return to main tab
                        flash("Shot Config %s submitted" % data.get("name"), "message")
                        active_tab = 'main'
                        form=None
                    else: # "Save and Continue
                        #good submit return to cap tab
                        flash("Shot Config %s updated" % data.get("name"), "message")
                        active_tab = 'cap'
            else: # form didn't validate return with form for inspection
                errmsg = "Check your config for errors:\n"
                for n in form.errors.keys():
                    if n == "file_settings":
                        cap_panel = 'file'
                    elif n=="shot_settings":
                        cap_panel = 'shot'
                flash(errmsg, "error")
                active_tab = 'cap'

        return (active_tab,cap_panel,form)
        
        
 # This will populate the cap_form with a config if given   
    def update_cap_form(self, cfg_id=None):
        
        cap_form = CaptureParamsForm(id="cap")   
        if cfg_id is not None:
            cfg = Config.query.get(cfg_id)
            icfg = cfg.args
            cap_form.name.data = cfg.name
            # file_setting_form            
            cap_form.file_settings.sub_dir.data = icfg.get("sub_dir", "")
            cap_form.file_settings.date_dir.data = icfg.get("date_dir", "Daily")
            cap_form.file_settings.date_dir_nested.data = icfg.get("date_dir_nested", False)
            cap_form.file_settings.image_type.data = icfg.get("image_format", "tif")
            cap_form.file_settings.file_prefix.data = icfg.get("file_prefix", "jai")            
            # rgb_settings
            rgb_conf = icfg.get("rgb",{})
            cap_form.rgb_settings.pixel_format.data = rgb_conf.get("pixel_format", "BayerRG8")
            cap_form.rgb_settings.ob_mode.data = rgb_conf.get("ob_mode", False)
            # nir_settings
            nir_conf = icfg.get("nir",{})
            cap_form.nir_settings.pixel_format.data = nir_conf.get("pixel_format", "Mono8")
            cap_form.nir_settings.ob_mode.data = nir_conf.get("ob_mode", False)
            # shot_settings
            shots = icfg.get("sequence", [])
            if shots is not None:
                exp=[]
                gain=[]
                for s in shots:
                    exp.append(str(s.get("exposure_time")))
                    g = s.get("gain")
                    if g is not None:
                        gain.append(str(g))
                if len(gain) == 0:
                    gain.append('0')
                cap_form.shot_settings.exposure.data = "\n".join(exp)
                cap_form.shot_settings.gain.data = '\n'.join(gain)
            
        return cap_form            
            
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
                kwargs['rgb']= {'pixel_format': 'BayerRG8', 'ob_mode': form.obmode.data}
                kwargs['nir']= {'pixel_format': 'Mono8', 'ob_mode': form.obmode.data} 
                kwargs['sequence']={ 'exposure_time': int(form.exposure.data), 'gain': int(form.gain.data)}
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
        
    def do_device_reset(self):
        from flask import flash,redirect
        self.device_reset()      
        flash("Issued Device Reset")
        return redirect('/phenocam')
        
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
                        'rgb':{'pixel_format': 'BayerRG8', 'ob_mode': False},
                        'nir':{'pixel_format': 'Mono8','ob_mode': False},      
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
       
    # Dont seem to be able to add other endpoints 
    # so we have to handle it all here
    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request
        
        if not self.initalized:
            flash("PhenoCam has not been properly initalized! See Settings Tab", 'error' )
        d = self._powerdelay   
        active_tab = 'main'
        cap_cfg = None
        cap_form = None
        cap_panel = 'file'
        #check for button actions on main
        action = request.args.get('action')
        if action is not None:
            if action == "reset":
                return self.do_device_reset()
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
            #change the init config
            if form_type == 'init':
                active_tab = self.update_init_model(request.form)     
            # cap config added or editied
            elif form_type == 'cap':
                active_tab,cap_panel,cap_form = self.update_cap_model(form_data)
             # config selected from list, so load it up.    
            elif form_type == 'cap_list':
                active_tab = 'cap'
                #This gets the id of selected config
                if form_data.get('config')=='__None':
                    cap_cfg=None
                else:
                    cap_cfg = int(form_data.get('config'))
                    
            elif form_type == 'test':
                return self.do_test(form=request.form)           
                    
        #load init form           
        init_form = self.update_init_form()                
        
        #runconfiglistform lets us load saved configs for editing
        #not ajax just reload
        if cap_cfg is not None:
            selected = Config.query.get(cap_cfg)
        else:
            selected = None
            
        #run_list = RunConfigListForm(id="run_list", config=selected)
        cap_list = CapConfigListForm(id="cap_list", config=selected)
        #this adds on change which reloads the form with data
        cap_opts = {
                'widget_args':{
                    'config': {
                        'onchange': 'this.form.submit()'
                    }                
                }        
        }
       
        
        #now load run form with selected config or nothing.
       # run_form = self.update_run_form(run_cfg)   
        #load /update cap form 
        if cap_form is None:
            cap_form = self.update_cap_form(cap_cfg) 
        
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
            cap_form = cap_form,
            active_tab = active_tab,
            return_url = "/phenocam/",
            cap_list=cap_list,
            cap_opts=cap_opts,
            cap_panel=cap_panel,
            delay=d
            )