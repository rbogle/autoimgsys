# -*- coding: utf-8 -*-
from ais.lib.task import Task
import datetime,subprocess
import pyinotify

class CalledProcess(object):
        
    def __init__(self, **kwargs):
        self.cmd = kwargs.get('cmd', "")
        self.returncode= kwargs.get('returncode', 0)
        self.output= kwargs.get('output', "")
    
    def cast(self, CalledProcessError):

        self.cmd = CalledProcessError.cmd
        self.output = CalledProcessError.output
        self.returncode = CalledProcessError.returncode
    
    def tostr(self):
        return "%s returns: %i,  %s" %(self.cmd, self.returncode, self.output)

class Rsync(object):

    def __init__(self, **kwargs):
        self.rsync_path = kwargs.get('rsync_path', "/usr/bin/rsync") 
               
    def sync(self, **kwargs):
        src = kwargs.get("src", "")
        dst = kwargs.get("dst", "")
        opts = kwargs.get("opts", "")
        excl = kwargs.get("excl", "")
        cmd = self.rsync_path+" -a"
        
        # build excludes list for cmd
        if excl != "":
            excludes =""
            excl_list = excl.split(',')
            for e in excl_list:
                excludes += " --exclude=%s" %e.strip()
            cmd+=excludes

        # add additional opts 
        if opts != "":
            cmd+=" %s" %opts
            
        src = " "+src            
        dst = " "+dst     
        cmd = cmd+src+dst  
        
        cp=CalledProcess(cmd=cmd)    
        try:
            cp.output = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT).splitlines()
        except subprocess.CalledProcessError as cpe:
            cp.cast(cpe)    
        return cp

class SyncEvent(pyinotify.ProcessEvent):
    
    def my_init(self, **kargs):
        self.sync = Rsync().sync
        
    def process_default(self, event):
        # TODO see pytinotify.py and inotify threadednotifier.py
        pass
        

class Utility(Task):
    
    def __init__(self, **kwargs):
        super(Utility, self).__init__(**kwargs)
        self.rsync = Rsync().sync
        self.syncevt = SyncEvent()
        self.watchman = pyinotify.WatchManager()
        self.notifier = None
       
    def run(self, **kwargs):     
        self.last_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')	              
        self.logger.debug("sync.utility.run called %s" %kwargs) 
        result = self.rsync(**kwargs)
        self.logger.info(result.output)

    def realtime_start(self):
                # TODO see pytinotify.py and inotify threadednotifier.py
        pass
    
    def realtime_stop(self):
                # TODO see pytinotify.py and inotify threadednotifier.py
        pass
        
 