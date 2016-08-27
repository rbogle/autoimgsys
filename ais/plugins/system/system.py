# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from flask import Markup, jsonify
from ais.ui import config
from flask.ext.admin.form import BaseForm
from wtforms import SelectField,HiddenField,BooleanField,StringField
from flask.ext.admin.form.fields import DateTimeField
import pytz
from tzlocal import reload_localzone
import ais.plugins.system.utility as utility

def get_tzlist():
    tzlist =list()
    tzs = pytz.common_timezones
    for tz in tzs:
        tzlist.append((tz,tz))
    return tzlist

class DateTimeForm(BaseForm):
    id = HiddenField()
    datetime = DateTimeField("New Date and Time")
    timezone = SelectField("Timezone", choices = get_tzlist(), default= lambda: reload_localzone().zone)

class PartitionForm(BaseForm):
    id = HiddenField()
    part = HiddenField()
    device = StringField("Device", description="The device to mount")
    mnt_pt = StringField("Mount", description="Mount device on this directory in the datastore: "+config.DISKSTORE, default="tmp" )    
    fstype = SelectField("Filesystem", description="Filesystem Format of disk", choices=[("ext4","Linux: ext4"),("vfat","Universal: FAT32"), ("ntfs","Windows: NTFS")])    
    persist = BooleanField("Persist", description="Make this mount persist accross reboots?", default=False)
    mount = BooleanField("Mount Now", default=False, description="Mount this directory now?")
    
    
class System(utility.Utility):
    
    def __init__(self, **kwargs):
        super(System, self).__init__(**kwargs)
        self.enabled = True
        self.viewable = True
        self.widgetized = True
        self.use_filestore = True
        self.use_sqllog = True
        self.view_template = self.path+'/system.html'
        self.widget_template = self.path+'/sys_widget.html'
    
    @expose('/', methods=('GET', 'POST'))
    def plugin_view(self):  
        from flask import request,flash  
        from flask.ext.admin import helpers as h
        
        action = request.args.get('action', None)
        modal = request.args.get('modal', None)
        active_tab = request.args.get('tab', 'sys')
        args = request.args
     
        #some form submitted
        if h.is_form_submitted():
            form_data = request.form
            form_type = form_data.get('id')
            
            if form_type == "datetime":
                flash("Date Time has been configured")
                self._conf_datetime(form_data)          
            if form_type == "partition":
                flash("Changing Mount for %s on %s" %(form_data.get('part'),form_data.get('mnt_pt')))
                self._change_mount(form_data)                       
            
        #handle actions
        if action is not None:
            if action == "get_events":
                flash("Events Log will download shortly.")                
                return self._download_events()
            if action == 'get_logs':
                flash("Logs will download shortly.")
                return self._download_logs()
            if action == 'reboot_sys':
                flash("reboot requested", "success")
                self._reboot_sys()
            if action == 'reset_ais':
                flash("Reset of AIS requested")
                self._reset_sys()
 
        #return modal dialog     
        if modal is not None:
            return self.get_widget_modal(modal, args)
        #return default page    
        p = [
            ('sys',self.path+"/sys_panel.html","System"),
            ('dsk',self.path+"/dsk_panel.html","Storage"),
            ('net',self.path+"/net_panel.html","Networking")
        ]
        d = self._get_device_info()

        w = self.get_widgets()
        i = self._get_sys_info()
        
        return self.render(self.view_template, info=i, widgets=w, panels=p, disks=d, active=active_tab)
    
    def get_widget_modal(self, name, kwargs):
        if name == 'reboot':
            return self.get_reboot_modal()
        if name == 'reset':
            return self.get_reset_modal()
        if name == 'datetime':
            return self.get_datetime_modal()
        if name == 'partition':
            return self.get_partition_modal(kwargs)
    
    def get_widgets(self):
        return [
            self.reboot_sys_widget(),
            self.reset_sys_widget(),
            self.set_datetime_widget(),
            self.download_events_widget(),
            self.download_logs_widget(),
            #self.upload_firmware_widget()
        ]

    def get_sys_info_widget(self):
        name = 'System Info'
        info = self._get_sys_info()
        body = Markup("<dl>")
        for k,v in info.iteritems():
            body += Markup("<dt>"+k+": </dt>")
            body += Markup("<dd>"+v+"</dd>")
        body += Markup("</dl>")
        action = ""
        return [name, body, action]
        
    def reboot_sys_widget(self):
        name = "Restart System"
        body = "Immediately reboot the system"
        action = Markup("<a id='reboot' class='btn btn-danger' data-toggle='modal' data-target='#sys-modal'>Reboot</a>")
        return [name, body, action]
    
    def download_events_widget(self):
        name = "Events"
        body = "Download all event logs"
        action = Markup("<a id='events' class='btn btn-primary' href='?action=get_events'>Download</a>")
        return [name, body, action]
    
    def download_logs_widget(self):
        name = "System Log"
        body = "Download all system logs"
        action = Markup("<a id='logs' class='btn btn-primary' href='?action=get_logs'>Download</a>")
        return [name, body, action]
    
    def reset_sys_widget(self):
        name = "Reset System"
        body = Markup("Reset the AIS system to the default settings.") 
        action = Markup("<a id='reset' class='btn btn-danger' data-toggle='modal' data-target='#sys-modal''>Reset</a>")
        return [name, body, action]
    
    def set_datetime_widget(self):
        name = "Configure Date & Time"
        body = "This configure the system time settings"
        action = Markup("<a id='datetime' class='btn btn-primary' data-toggle='modal' data-target='#sys-modal''>Configure</a>")
        return [name, body, action]
    
    def upload_firmware(self):
        pass
         
    def get_reboot_modal(self):
        return jsonify({
            'title' : "Hardware Reboot",
            'title_emph' : "btn-danger",
            'body' : "This system will restart and be unavailable for approx \
                1 minute.<br/>Are you sure you want to reboot?", 
            'url' : "/system?action=reboot_sys",
            'url_emph' : "btn-danger"
        }) 
        
    def get_reset_modal(self):
        return jsonify({
            'title':'System Reset',
            'title_emph': 'btn-danger',
            'body':"This will delete all stored configurations and tasks, and restart the AIS service",
            'url':'/system?action=reset_ais',
            'url_emph':'btn-danger'
        })
        
    def get_datetime_modal(self):
        title ='Set System Date and Time'
        f = DateTimeForm(id="datetime")
        ru = "/system"
        body = self.render(self.path+'/modal_form.html', aform=f, return_url =ru)
        url = ""
        return jsonify({ 'title': title, 'body': body, 'url': url})

    def get_partition_modal(self, args):
        title = "Edit Partition Mounting"
        f = PartitionForm(id="partition")
        f.device.data= args.get('partition', '/dev/null') #disabled doesnt come back
        f.part.data = args.get('partition', '/dev/null') #hidden comes back
        f.mount.data = args.get('mounted', False)
        mnt_pt = args.get('mnt_pt', 'tmp')
        if mnt_pt == "":
            mnt_pt='tmp'
        f.mnt_pt.data = mnt_pt
        f.fstype.data = args.get('fs_type', None)
        f.persist.data = args.get('persist', False)
        
        o={'widget_args':{
                'device':{
                    'disabled':'true'
                }
           }
        }
        body=self.render(self.path+"/modal_form.html", aform=f, opts=o)
        return jsonify({'title':title, 'body':body, 'url':""})
    