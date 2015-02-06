# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from flask import Markup, jsonify, redirect
from flask.ext.admin.form import BaseForm
from wtforms import SelectField, TextField
from flask.ext.admin.form.fields import DateTimeField
from ais.lib.task import Task
from ais.ui.models import Event,Log,Plugin
from ais.ui import config
import subprocess,datetime,pytz,re,os,glob
from tzlocal import get_localzone, reload_localzone
from collections import OrderedDict

def get_tzlist():
    tzlist =list()
    tzs = pytz.common_timezones
    for tz in tzs:
        tzlist.append((tz,tz))
    return tzlist

class DateTimeForm(BaseForm):

    datetime = DateTimeField("New Date and Time")
    timezone = SelectField("Timezone", choices = get_tzlist(), default= lambda: reload_localzone().zone)
            
    
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
        ifcfg = subprocess.check_output('/sbin/ifconfig').split('\n\n')
        ifaces = ""

        for i in ifcfg:
            if i != "":    
                net = re.search("^[0-9a-z]*\w",i)
                if net is not None:
                    net = net.group(0)
                addr= re.search("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",i)
                if addr is not None:
                    addr = addr.group(0)
                    ifaces += Markup(net+": "+addr+"<br/>")
#        for i in range(len(ifcfg))[0::10]:
#            data=','.join( ifcfg[i:i+2]).split()
#            data[7] = data[7].split(":")[1]
#            ifaces += Markup(data[0]+": "+data[7]+"<br/>")
        return OrderedDict([('Hostname',hostname),('Kernel',kernel),
                            ('Time', now),('Up-Time', uptime),('Disks', disks), ('Net',ifaces)])
    
    def _reset_sys(self):
        
        db_path = config.DATABASE_PATH
        
        try:
            pid = subprocess.check_output(['pgrep', 'ais_service'])
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
            return         
        cmd = "sudo kill -HUP %s" %pid
        #delete dbs         
        for f in glob.glob(db_path+"*.sqlite"):
            os.remove(f)
        #now hup the service to restart
        try:
            self.logger.debug("Doing: %s" %cmd)
            subprocess.check_output(cmd.split())
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
    
    def _reboot_sys(self):
        self.logger.info("System Module: Reboot Requested")
        command = "sudo shutdown -r now"
        try:
            subprocess.check_output(command.split())
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
            
    def _conf_datetime(self, form):
        tz=form.get('timezone')
        dt = form.get('datetime')
        self.logger.info("tz: %s, datetime: %s" %(tz,dt))
        #handle tz
        tz_now = reload_localzone().zone
        if tz!=tz_now:
            self._set_timezone(tz)
        #handle datetime
        if dt!="":
            self._set_datetime(dt)
        #handle ntp 
            
    def _set_datetime(self, datestr):
        cmd = "sudo date --set %s" %datestr
        try:
           output= subprocess.check_output(cmd.split())
           self.logger.info("DateTime set to: %s" %output)
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
            
    def _set_timezone(self, tzname):
        #TODO specific to Ubuntu distro
        cmds=[
            "sudo cp /etc/localtime /etc/localtime.old",
            "sudo ln -sf /usr/share/zoneinfo/%s /etc/localtime" %tzname,
            "sudo mv /tmp/timezone /etc/timezone"
        ]
        #make a tmp file then mv it over to /etc/timezone
        with open('/tmp/timezone', 'wt') as outf:
            outf.write(tzname+'\n')        
        try:        
            for c in cmds:
                subprocess.check_output(c.split())
            self.logger.info("Timezone Changed to %s"%tzname)
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
            
    def _download_logs(self):
        import StringIO,csv
        from flask import send_file
        sio = StringIO.StringIO()
        cw = csv.writer(sio)
        cw.writerow(['Datetime','Plugin','Module', 'Level', 'Msg', 'Trace'])
        for log in Log.query.all():
            cw.writerow([log.created, log.logger, log.module, log.level, log.msg, log.trace])
        sio.seek(0)
        return send_file(sio, attachment_filename="AIS_Logs.csv", as_attachment=True)
    
    def _download_events(self):
        import StringIO,csv
        from flask import send_file
        sio = StringIO.StringIO()
        cw = csv.writer(sio)
        cw.writerow(['Datetime','Plugin','Event', 'Msg', 'Trace'])
        for evt in Event.query.all():
            pn = evt.plugin.name
            cw.writerow([evt.datetime, pn, evt.code, evt.msg, evt.trace])
        sio.seek(0)
        return send_file(sio, attachment_filename="AIS_Events.csv", as_attachment=True)
        
    