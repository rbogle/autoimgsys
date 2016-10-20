# -*- coding: utf-8 -*-
from ais.lib.task import Task
from ais.ui.models import Config,Plugin
from ais.ui import db
import datetime,subprocess,os,logging,copy,time
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
        self.logger = logging.getLogger(self.__class__.__name__)   
         
    def sync(self, **kwargs):
        src = kwargs.get("src", "")
        dst = kwargs.get("dst", "")
        opts = kwargs.get("opts", "")
        excl = kwargs.get("excl", "")
        wait = kwargs.get("wait", True)
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
        if wait:
            try:
                cp.output = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT).splitlines()
            except subprocess.CalledProcessError as cpe:
                self.logger.error(cpe.message)
                cp.cast(cpe)
        else:
            try:
                subprocess.Popen(cmd.split())
            except subprocess.CalledProcessError as cpe:
                self.logger.error(cpe.message)
                cp.cast(cpe)
        return cp

class SyncEvent(pyinotify.ProcessEvent):
    
    def my_init(self, **kargs):
        self.sync = kargs.get("sync_method", Rsync().sync)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_wpaths(self):  
        sync_configs = Config.query.join(Plugin).filter(Plugin.name=='Data Sync').filter(Config.role=="Runtime").all()
        wpaths = list()
        for c in sync_configs:
            if c.args.get('mkrt', False):
                wpaths.append(c.args)
        return wpaths
    
    def process_default(self, event):
        wpaths = self.get_wpaths()
        self.logger.debug("caught %s on %s" %(event.maskname, os.path.join(event.path, event.name)))
        for apath in wpaths:
            if os.path.realpath(apath['src']) in os.path.realpath(event.path):
                self.sync(**apath)
                break
        

class Utility(Task):
    
    def __init__(self, **kwargs):
        super(Utility, self).__init__(**kwargs)
        self.rsync = Rsync(**kwargs)
        self.syncevt = SyncEvent(sync_method = self.rsync.sync)
        self.watchman = None #pyinotify.WatchManager()
        self.watch_delay = kwargs.get("delay", 30)
        self.notifier = None
        default_events = [
            "IN_CLOSE_WRITE",
            "IN_CREATE",
            "IN_DELETE",
            "IN_MOVED_FROM",
            "IN_MOVED_TO"
        ]
        self.events = kwargs.get("watch_events", default_events)

    def run(self, **kwargs):     
        self.last_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')	              
        self.logger.debug("sync.utility.run called %s" %kwargs) 
        result = self.rsync.sync(**kwargs)
        self.logger.info(result.output)
    
    def get_rtsync(self):
        if self.notifier is not None:
            return self.notifier.isAlive()
        return False

    def get_mask(self):
        return reduce(lambda x,y: x|y, [pyinotify.EventsCodes.ALL_FLAGS[e] for e in self.events])

    def add_watch(self, apath):
        if self.get_rtsync():
            wpath = copy.deepcopy(apath)
            mask = self.get_mask()
            self.watchman.add_watch(str(wpath['src']), mask, rec=True, auto_add=True)
            wpath['wait']=False
            self.rsync.sync(**wpath)

    def remove_watch(self,apath):
        if self.get_rtsync():
            wd = self.watchman.get_wd(str(apath['src']))
            if wd is not None:
                self.watchman.rm_watch(wd, rec=True)
    
    def start_rtsync(self):
        if self.notifier is None:
            self.watchman = pyinotify.WatchManager()
            self.notifier = pyinotify.ThreadedNotifier(self.watchman, self.syncevt, read_freq=self.watch_delay)
            self.notifier.coalesce_events(True)
            mask = self.get_mask()
            wpaths = self.syncevt.get_wpaths()
            for awpath in wpaths:
                self.logger.debug("adding %s to sync watches" %awpath['src'])
                wpath = copy.deepcopy(awpath)
                self.watchman.add_watch(wpath['src'], mask, rec=True, auto_add=True)
                # do an initial sync, dont wait for rsync to finish.
                wpath['wait']=False
                self.rsync.sync(**wpath)
            self.logger.debug("starting notifier...")
            self.notifier.start()
        else:
            self.logger.debug("start_rtsync called by notifier not none.")
            
    def stop_rtsync(self):
        if self.notifier is not None:
            watches = self.syncevt.get_wpaths()
            for watch in watches:
                wd = self.watchman.get_wd(watch['src'])
                self.watchman.rm_watch(wd, rec=True)
            self.notifier.stop()
            #wait for thread to closeout before destroying objs.
            while self.notifier.isAlive():
                time.sleep(1)
            self.notifier = None
            self.watchman = None

        