import ais.plugins.jai.jai as jai #inhertiancew path due to Yapsy detection rules
from ais.ui.models import Config, Plugin
from wtforms import Form,StringField,HiddenField,TextAreaField, BooleanField,IntegerField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask.ext.admin import expose
import logging, datetime, ast

logger = logging.getLogger(__name__)

class RunConfigListForm(Form):
    id = HiddenField()
    config = QuerySelectField("Stored Configs:", allow_blank=True, blank_text="Create New", 
                          query_factory=lambda: Config.query.filter_by(plugin="PhenoCam", role="Runtime").all()                          
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
    
class PhenoCam(jai.JAI_AD80GE): #note inheritance path due to Yapsy detection rules
    
    def __init__(self,**kwargs):
        """Initializes camera instance
        
           Args:
               **kwargs Named arguments to configure the camera(s)
                   Sensors: dict of name: mac address for each of the sensors on board
        """
        logger.debug("Phenocam __init__ called")
        super(PhenoCam,self).__init__(**kwargs) 
        self.viewable = True
        self.widgetized = True
        self.view_template = self.path+'/phenocam.html'
        self.widget_template = self.path+'/pheno_widget.html'
        
        
    def update_init_model(self, form):
        from flask import flash,request
        #load init config stored
        icfg = Config.query.filter_by(plugin=self.name, role="Initalize").first()
        if icfg is None:
            icfg = Config(plugin=self.name, role="Initalize", args={}, name="PhenoCam Init")
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
            new_args['relay_port'] = form.get('relay_port')
            new_args['relay_delay'] = form.get('relay_delay')
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
            flash("Init Form submitted", "message")
            return 'main'

    def update_init_form(self):
        #load init config stored
        icfg = Config.query.filter_by(plugin=self.name, role="Initalize").first()
        if icfg is None:
            icfg = Config(plugin=self.name, role="Initalize", args={}, name="PhenoCam Init")
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
            form.relay_delay.data = icfg.args.get("relay_delay", "")
            form.relay_port.data = icfg.args.get("relay_port", "")
        else:
            form.use_relay = False
        return form
    
    def update_run_model(self,form):
        
        from flask import flash,request
        if form.get('name') != "":
            icfg = Config.query.filter_by(plugin=self.name, role="Runtime", name=form.get("name")).first()
            if icfg is None:
                icfg = Config(plugin=self.name, role="Runtime", name=form.get('name'))
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

    def do_test(self):
        from flask import flash, redirect
        flash("Test Requested")
        return redirect('/phenocam')
    
    def do_reinit(self):
        from flask import flash, redirect
        flash("Initialization Requested")
        return redirect('/phenocam')
        
    def do_status(self):
        from flask import flash, redirect
        flash("Status update Requested")
        return redirect('/phenocam')   
        
    @expose('/', methods=('GET','POST'))
    def plugin_view(self):
        
        from flask.ext.admin import helpers as h
        from flask import flash,request
        
        if not self.initalized:
            flash("PhenoCam has not been properly initalized! See Settings Tab", 'error' )
            
        active_tab = 'main'
        #check for button actions on main
        run_cfg = None
        action = request.args.get('action')
        if action is not None:
            if action == "reinit":
                self.do_reinit()
            if action == "test":
                return self.do_test()   
            if action == "status":
                return self.do_status()
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
            run_form=run_form
            )