# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from flask import Markup
from ais.lib.task import Task
import subprocess,datetime
from collections import OrderedDict


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
        w = self.get_widgets()
        i = self._get_sys_info()
        return self.render(self.view_template, info=i, widgets=w)
        
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
        action = Markup("<a id='reboot-btn' class='btn btn-danger'>Reboot</a>")
        return [name, body, action]
    
    def download_events_widget(self):
        name = "Events"
        body = "Download all event logs"
        action = Markup("<a id='eventsdl-btn' class='btn btn-primary'>Download</a>")
        return [name, body, action]
    
    def download_logs_widget(self):
        name = "System Log"
        body = "Download all system logs"
        action = Markup("<a id='logsdl-btn' class='btn btn-primary'>Download</a>")
        return [name, body, action]
    
    def reset_sys_widget(self):
        name = "Reset System"
        body = Markup("Reset the AIS system to the default settings.") 
        action = Markup("<a id='reset-btn' class='btn btn-danger'>Reset</a>")
        return [name, body, action]
    
    def set_datetime_widget(self):
        name = "Configure Date & Time"
        body = "This configure the system time settings"
        action = Markup("<a id='settime-btn' class='btn btn-primary'>Configure</a>")
        return [name, body, action]
    
    def upload_firmware(self):
        pass
    
    def _get_sys_info(self):
        self.logger.info("System Module: Sys Info Requested")
        now = subprocess.check_output("date")
        uptime = subprocess.check_output("uptime")
        hostname = subprocess.check_output("hostname")
        kernel = subprocess.check_output(['uname', '-sr'])
        di = subprocess.check_output(['df','-h','-t', 'ext4']).split('\n')
        disks = ""
        for l in di[1:]:
            disks += Markup(l+"<br/>")
        return OrderedDict([('Hostname',hostname),('Kernel',kernel),('Time', now),('Up-Time', uptime),('Disks', disks)])
    
    def _reboot_sys(self):
        self.logger.info("System Module: Reboot Requested")
        command = "/usr/bin/sudo /sbin/shutdown -r now"
        subprocess.call(command.split(),shell=True)
