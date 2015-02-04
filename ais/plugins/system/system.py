# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from flask import Markup, jsonify
from flask.ext.admin.form import BaseForm
from wtforms import SelectField, TextField
from flask.ext.admin.form.fields import DateTimeField
from ais.lib.task import Task
import subprocess,datetime,pytz
from tzlocal import get_localzone
from collections import OrderedDict

def get_tzlist():
    tzlist =list()
    tzs = pytz.common_timezones
    for tz in tzs:
        tzlist.append((tz,tz))
    return tzlist

def get_currtz():
    return get_localzone().zone


class DateTimeForm(BaseForm):

    datetime = DateTimeField("New Date and Time")
    timezone = SelectField("Timezone", choices = get_tzlist(), default=get_currtz())
            
    
class System(Task):
    
    def __init__(self, **kwargs):
        super(System, self).__init__(**kwargs)
        self.enabled = True
        self.viewable = True
        self.widgetized = True
        self.use_filestore = True
        self.use_sqllog = True
        self.view_template = self.path+'/system.html'
        self.widget_template = self.path+'/sys_widget.html'

    def run(self, **kwargs):
        pass
    
    @expose('/', methods=('GET', 'POST'))
    def plugin_view(self):  
        from flask import request,flash  
        from flask.ext.admin import helpers as h
        
        action = request.args.get('action', None)
        modal = request.args.get('modal', None)
        #datetime form submitted
        if h.is_form_submitted():
            flash("Date Time has been configured")
            self._conf_datetime(request.form)          
            
        #handle actions
        if action is not None:
            if action == "get_events":
                flash("Events Log will download shortly.")                
                #return self._download_events()
            if action == 'get_logs':
                flash("Logs will download shortly.")
                #return self._download_logs()
            if action == 'reboot_sys':
                flash("reboot requested", "success")
            if action == 'reset_ais':
                flash("Reset of AIS requested")
 
        #return modal dialog     
        if modal is not None:
            return self.get_widget_modal(modal)
        #return default page    
        w = self.get_widgets()
        i = self._get_sys_info()
        return self.render(self.view_template, info=i, widgets=w)
    
    def get_widget_modal(self, name):
        if name == 'reboot':
            return self.get_reboot_modal()
        if name == 'reset':
            return self.get_reset_modal()
        if name == 'datetime':
            return self.get_datetime_modal()
    
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
        f = DateTimeForm()
        ru = "/system"
        body = self.render(self.path+'/datetime.html', dtform=f, return_url =ru)
        url = ""
        return jsonify({ 'title': title, 'body': body, 'url': url})

        
    def _get_sys_info(self):
        #self.logger.info("System Module: Sys Info Requested")
        now = subprocess.check_output("date")
        #uptime
        with open('/proc/uptime', 'r') as f:
            us = float(f.readline().split()[0])
            uptime = str(datetime.timedelta(seconds = int(us)))
            
        hostname = subprocess.check_output("hostname")
        kernel = subprocess.check_output(['uname', '-sr'])
        #disk info
        di = subprocess.check_output(['df','-h','-t', 'ext4']).split('\n')
        disks = ""
        for l in di[1:]:
            l= l.split()
            if len(l)>0:
                l = l[5]+'\t'+l[1]+'\t'+l[4]+'\t'+l[0]
                disks += Markup(l+"<br/>")
        #eth info        
        ifcfg = subprocess.check_output('/sbin/ifconfig').split('\n')
        ifaces = ""
        for i in range(len(ifcfg))[0::10]:
            data=','.join( ifcfg[i:i+2]).split()
            data[7] = data[7].split(":")[1]
            ifaces += Markup(data[0]+": "+data[7]+"<br/>")
        return OrderedDict([('Hostname',hostname),('Kernel',kernel),
                            ('Time', now),('Up-Time', uptime),('Disks', disks), ('Net',ifaces)])
    
    def _reboot_sys(self):
        self.logger.info("System Module: Reboot Requested")
        command = "/usr/bin/sudo /sbin/shutdown -r now"
        subprocess.call(command.split(),shell=True)

    def _conf_datetime(self, form):
        tz=form.get('timezone')
        dt = form.get('datetime')
        self.logger.info("tz: %s, datetime: %s" %(tz,dt))
        #handle tz
        tz_now = get_localzone().zone
        if tz!=tz_now:
            self._set_timezone(tz)
        #handle datetime
        if dt!="":
            self._set_datetime(dt)
        #handle ntp 
    def _set_datetime(self, datestr):
        pass
    
    def _set_timezone(self, tzname):
        pass
       
    def _download_logs(self):
        pass
    
    def _download_events(self):
        pass
    