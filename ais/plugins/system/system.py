# -*- coding: utf-8 -*-
from flask.ext.admin import expose
from flask import Markup
from ais.lib.task import Task
import subprocess,datetime

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
        return self.render(self.view_template, widgets=w)
        
    def get_widgets(self):
        return [
            self.get_sys_info_widget(),
            self.reboot_sys_widget(),
            self.reset_sys_widget(),
            self.set_datetime_widget(),
            self.download_event_widget(),
            self.download_logs_widget(),
            self.upload_firmware_widget()
        ]

    def get_sys_info_widget(self):
        name = 'System Info'
        info = self._get_sys_info()
        body =""    
        action = ""
        return [name, body, action]
        
    def reboot_sys_widget(self):
        name = "Restart System"
        body = "This will immediately reboot the system"
        action = Markup("")
        return [name, body, action]
    
    def download_events_widget(self):
        pass
    
    def download_logs_widget(self):
        pass
    
    def reset_sys_widget(self):
        pass
    
    def set_datetime_widget(self):
        pass
    
    def upload_firmware(self):
        pass
    
    def _get_sys_info(self):
        self.logger.info("System Module: Sys Info Requested")
        now = datetime.datetime.now().ctime()
        uptime = subprocess.check_output("uptime")
        hostname = subprocess.check_output("hostname")
        kernel = subprocess.check_output(['uname', '-sr'])
        return {'now': now, 'uptime': uptime, 'hostname':hostname, 'kernel':kernel}
    
    def _reboot_sys(self):
        self.logger.info("System Module: Reboot Requested")
        command = "/usr/bin/sudo /sbin/shutdown -r now"
        subprocess.call(command.split(),shell=True)
