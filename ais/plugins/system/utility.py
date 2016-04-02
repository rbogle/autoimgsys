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
from flask import Markup
import StringIO,csv
from flask import send_file

class Utility(Task):
    
    def __init__(self, **kwargs):
        super(Utility, self).__init__(**kwargs)    
    
    def run(self, **kwargs):
        pass
    
    def _read_fstab(self):
        fstabs = list()
        with open("/etc/fstab") as f:
            for line in f:
                if not line.strip().startswith("#"):
                    l = line.rstrip().split()
                    fstabs.append(l)
        return fstabs
        
    def _get_blkids(self,device=None):
        pass
    
    def _get_disk_info(self):
       disk_info = self._get_part_info()
       mounts = self._get_mount_info()
       for disk in disk_info:
           for pname,pinfo in disk['parts'].iteritems():
               if mounts.has_key(pname):
                   pinfo.update(mounts[pname])
                   pinfo['mounted']=True
               else:
                   pinfo['mounted']=False
       return disk_info

    def _get_mount_info(self):
        cmd = "mount -l -t ext2,ext3,ext4,vfat,fuseblk,hfsplus"
        try:
            outp = subprocess.check_output(cmd.split()).splitlines()
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output) 
            return None
        fstabs = self._read_fstab()
        mounts = dict()
        if outp is not None:
            for line in outp:
                info = line.split(" ")
                persist=False
                for perm in fstabs:
                    print "mount dir: %s fstab dir: %s" %(info[2],perm[1])
                    if info[2] == perm[1]:
                        persist = True
                        fstab_dev = perm[0]
                try:
                    cmd="df -h %s" % info[2]
                    usage =subprocess.check_output(cmd.split()).splitlines()[1].split()
                except subprocess.CalledProcessError as cpe:
                    self.logger.error(cpe.output)                
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
                if persist:
                    mounts[info[0]]['fstab_dev']=fstab_dev
                    
        return mounts        
            
    def _get_part_info(self):
        cmd = "sudo parted -lm"
        disk_list = list()
        try:
            outp = subprocess.check_output(cmd.split()).splitlines()
        except subprocess.CalledProcessError as cpe:
            self.logger.error(cpe.output) 
            return None
        for l in outp:
            if l == "BYT;":
                disk = dict()
                disk['parts']=dict()
            elif l == "":
                disk_list.append(disk)
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
            #self.logger.debug("Doing: %s" %cmd)
            subprocess.check_output(cmd.split())
        except subprocess.CalledProcessError as cpe:
            exit()
    
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