# -*- coding: utf-8 -*-
"""
Created on Thu Mar 31 08:41:15 2016

@author: rbogle
"""

from ais.lib.task import Task
from ais.ui.models import Event,Log
from ais.ui import config
import subprocess,datetime,re,os,glob
from tzlocal import reload_localzone
from collections import OrderedDict
from flask import Markup, flash
import StringIO,csv,re
from flask import send_file 

class CalledProcess(object):
        
    def __init__(self, **kwargs):
        self.cmd = kwargs.get('cmd', "")
        self.returncode= kwargs.get('returncode', 0)
        self.output= kwargs.get('output', "")
    
    def cast(self, CalledProcessError):

        self.cmd = CalledProcessError.cmd
        self.output = CalledProcessError.output
        self.returncode = CalledProcessError.returncode
    
    
class Utility(Task):
    
    def __init__(self, **kwargs):
        super(Utility, self).__init__(**kwargs)    
    
    def run(self, **kwargs):
        pass
    
    def _read_fstab(self):
        fstabs = dict()
        with open("/etc/fstab") as f:
            for line in f:
                if not line.strip().startswith("#"):
                    l = line.rstrip().split()
                    fstabs[l[1]]=l[0]
        return fstabs
        
    def _get_blkids(self):
        cmd="sudo blkid"
        blkids=dict()
        try:
            outp = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT).splitlines()
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output) 
            return None
        for line in outp:
            info = line.split(" ")
            blkids[info[0].translate(None,':')]=info[1].translate(None,'\"')
        return blkids
            
    def _get_device_info(self, device=None):
       device_info = self._get_part_info()
       mounts = self._get_mount_info()
       for name,disk in device_info.iteritems():
           for pname,pinfo in disk['parts'].iteritems():
               if mounts.has_key(pname):
                   pinfo.update(mounts[pname])
                   pinfo['mounted']=True
               else:
                   pinfo['mounted']=False
       # only return partition or disk
       if device is not None:
           disk = device.translate(None, '0123456789')
           if disk in device_info:
               if (disk != device):        
                   device_info = device_info[disk]['parts'].get(device, None)
               else:
                   device_info = device_info[disk]
       return device_info

    def _get_mount_info(self):
        # first find all the currently mounted directories in userspace
        cmd = "mount -l -t ext2,ext3,ext4,vfat,fuseblk,hfsplus"
        try:
            outp = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT).splitlines()
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output) 
            return None
        #get fstab info. 
        fstabs = self._read_fstab()
        blkids = self._get_blkids()
        mounts = OrderedDict()
        #now get info for each mount pt. and check if its in fstab. 
        if outp is not None:
            for line in outp:
                info = line.split(" ")
                persist=False
                if info[2] in fstabs:
                    persist=True
                    fstab_dev = fstabs[info[2]]
                try:
                    cmd="df -h %s" % info[2]
                    usage =subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT).splitlines()[1].split()
                except subprocess.CalledProcessError as cpe:
                    self.logger.error(cpe.output) 
                    usage= ["df error"]*5 #This shouldn't be needed but just in case.
                mounts[info[0]]={
                    'part': info[0],
                    'dir': info[2],
                    'type': info[4],
                    'opts': info[5].translate(None, "()"),
                    'size': usage[1],
                    'used': usage[2],
                    'avail': usage[3],
                    'usedperc': usage[4],
                    'persist': persist
                }
                if info[0] in blkids:
                       mounts[info[0]]['uuid']=blkids[info[0]]              
                if persist:
                    mounts[info[0]]['fstab_dev']=fstab_dev                   
        return mounts 
             
    def _get_part_info(self):
        cmd = "sudo parted -lm"
        disk_list = OrderedDict()
        #disk_list = list()
        try:
            outp = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT).splitlines()
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output) 
            return None
        for l in outp:
            if l == "BYT;":
                disk = dict()
                disk['parts']=dict()
            elif l == "":
                disk_list[disk['device']]=disk
                #disk_list.append(disk)
            else:
                info = l.split(':')
                if '/dev' in info[0]:
                    disk['device'] = info[0]
                    disk['id'] = info[0].split('/')[-1]
                    disk['name']= info[6].replace(";","")
                    disk['size']=info[1]
                else:
                    disk['parts'][disk['device']+info[0]]={
                        'size': info[3],
                        'type': info[4],
                        'start': info[1],
                        'end': info[2]
                    }
        return disk_list
        
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
            pid = subprocess.check_output(['pgrep', 'ais_service'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
            return         
        cmd = "sudo kill -HUP %s" %pid
        #delete dbs         
        for f in glob.glob(db_path+"*.sqlite"):
            os.remove(f)
        #now hup the service to restart
        try:
            #self.logger.debug("Doing: %s" %cmd)
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as cpe:
            exit()
            
# TDDO make this async and return     
    def _reboot_sys(self):
        self.logger.info("System Module: Reboot Requested")
        command = "sudo shutdown -r now"
        try:
            subprocess.check_output(command.split(), stderr=subprocess.STDOUT)
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
           output= subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
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
                subprocess.check_output(c.split(), stderr=subprocess.STDOUT)
            self.logger.info("Timezone Changed to %s"%tzname)
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)
            
    def _download_logs(self):
        sio = StringIO.StringIO()
        cw = csv.writer(sio)
        cw.writerow(['Datetime','Plugin','Module', 'Level', 'Msg', 'Trace'])
        for log in Log.query.all():
            cw.writerow([log.created, log.logger, log.module, log.level, log.msg, log.trace])
        sio.seek(0)
        return send_file(sio, attachment_filename="AIS_Logs.csv", as_attachment=True)
    
    def _download_events(self):
        sio = StringIO.StringIO()
        cw = csv.writer(sio)
        cw.writerow(['Datetime','Plugin','Event', 'Msg', 'Trace'])
        for evt in Event.query.all():
            pn = evt.plugin.name
            cw.writerow([evt.datetime, pn, evt.code, evt.msg, evt.trace])
        sio.seek(0)
        return send_file(sio, attachment_filename="AIS_Events.csv", as_attachment=True)
        
    def _change_mount(self, args):
        for arg in args:
            self.logger.debug("%s -> %s" %(arg, args[arg]))
        fm_part = args.get('partition', None)
        fm_mnt_pt = args.get('mnt_pt', None)
        fm_mk_persist = args.get('persist', False)
        fm_mk_mnt = args.get('mount', False)
        mnt_info = self._get_device_info(part)
        if mnt_info:
            dev_mnt = mnt_info.get('mounted', False) 
            dev_persist = mnt_info.get('persist', False)
            dev_uuid = mnt_info.get('uuid', None)
            dev_mnt_pt = mnt_info.get('dir', None)

        path = config.DATASTORE+fm_mnt_pt

        
    def _mkdir(self, path):
        rval=True
        try:
            os.makedirs(path)
        except OSError as e:
            if not os.path.isdir(path): #path does not pre-exist. 
                rval=False    
                self.logger.error(e.output)
        return rval
        
    def _mkfs(self, device, fstype):
        pass
      
    def _edit_fstab(self, part, dest ):
        pass
    
    def _mount(self, device, dir=None, options=None):
        cmd = "sudo mount %s %s" %(device,dir)
        if options:
            cmd += "-o %s" %options
        cp= CalledProcess(cmd= cmd)
        try:
           cp.output = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
           self.logger.info("Mounted %s to: %s" %(device,dir))
        except subprocess.CalledProcessError as cpe:
            self.logger.error("Mount error: %s" %cpe.output)
            cp.cast(cpe)
        return cp
        
    def _umount(self, mount):
        cmd = "sudo umount %s" %(mount)
        cp=CalledProcess(cmd=cmd)
        try:
           cp.output = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
           self.logger.info("UnMounted %s" %(mount))
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output)  
            cp.cast(cpe)
        return cp