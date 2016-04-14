# -*- coding: utf-8 -*-
#
#    This software is in the public domain because it contains materials
#    that originally came from the United States Geological Survey, 
#    an agency of the United States Department of Interior.
#    For more information, see the official USGS copyright policy at
#    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
#
#   <author> Rian Bogle </author>
""" JAI module provides representations of JAI gigE cameras controlled by arvais 

    The first class is the JAI_AD80GE class subclased from ais.Task
    This device has two cameras one RGB visible and one Mono NIR.
"""    

from ais.plugins.jai.aravis import *
from ais.lib.task import PoweredTask
from ais.lib.relay import Relay
import pprint, time, cv2, traceback, datetime, os
from collections import OrderedDict

class Sensor(object):
    
    def __init__(self, **kwargs):
        self.name = kwargs.get("name",None)
        self.mac = kwargs.get("mac", None)
        self.cam = None

class JAI_AD80GE(PoweredTask):
    
    def run(self, **kwargs):
        """Initalizes camera system, configures camera, and collects image(s)
        
        Args:
            **kwargs: Named arguments to configure camera for shot(s)
                      Used keywords are the following:
                          
                date_pattern (opt) : passed as strftime format
                                    used for filename YYYY-MM-DDTHHMMSS
                file_prefix (opt) : Prefix for filename 'jai'
                date_dir (None, hourly, daily, monthly, yearly) : make subdirs for storage
                date_dir_nested (opt): make a separate nested subdir for each y,m,d,h or single subdir as yyyy_mm_dd_hh
                sub_dir (opt): add subdirectories to filestore
                timeout (opt) : millseconds to wait for image return
                sequence (opt): list of dictionaries with the following:
                                each dict given will be a numbered image
                exposure_time (opt) : image exposure time in uSec
                                        33319 (1/30th) default
                                        20 is min
                gain (opt) : 0-26db gain integer steps 0 default
                height (opt) : requested image height max default
                width (opt) : requested image width max default
                offset_x (opt) : requested image x offset 0 default
                offset_y (opt) : requested image y offest 0 default       
        """

        try: # we dont want to crash the ais_service so just log errors
        
           #we need to start camerasys as this is task callback
            if not self._started:   
                self.start()
            self.last_run['images']=list()
            self.last_run['config']=kwargs
            self.logger.debug("Shot config is:\n %s" % pprint.pformat(kwargs, indent=4))
            persist = kwargs.get("persist", False)
            datepattern = kwargs.get("date_pattern", "%Y-%m-%dT%H%M%S" ) 
            split = kwargs.get("date_dir",'Daily')
            nest = kwargs.get("date_dir_nested", False)
            subdir = kwargs.get("sub_dir", None)
            filename = self._gen_filename(kwargs.get('file_prefix', "jai"), 
                                 datepattern,  subdir=subdir, split = split, nest = nest)
            imgtype = kwargs.get("image_type", 'tif')
            sequence = kwargs.get('sequence', None)
            # Get the sensor configurations
            sensor_confs = {'rgb': kwargs.get("rgb", {}), 'nir': kwargs.get("nir", {})}
            for sname, sc in sensor_confs.iteritems():
                def_fmts = {'rgb': 'BayerRG8', 'nir': 'Mono8'}
                if sname in def_fmts.keys():
                    def_fmt = def_fmts.get(sname)
                    self._sensors[sname].cam.set_pixel_format_as_string(sc.get("pixel_format", def_fmt))   
                    ob_mode = sc.get('ob_mode', False)
                    if ob_mode:
                        self._sensors[sname].cam.write_register(0xa41c,1)
                    else:
                        self._sensors[sname].cam.write_register(0xa41c,0)                          
                #create frame bufer
                #self._sensors[sname].cam.create_buffers(1);        
                # start/stop acquisition have to be outside the capture loop.                        
                #self._sensors[sname].cam.start_acquisition_trigger() 
                #we need to put in the packet delay to improve reliability
                self._sensors[sname].cam.set_integer_feature("GevSCPD",4000)
                #and set sync mode for image capture 
                self._sensors[sname].cam.set_string_feature("SyncMode", "Sync")

                self._sensors[sname].cam.set_string_feature("AcquisitionMode", "SingleFrame") #no acquisition limits
                self._sensors[sname].cam.set_string_feature("TriggerSource", "Software") #wait for trigger t acquire image
                self._sensors[sname].cam.set_string_feature("TriggerMode", "On") #Not documented but necesary


            self.last_run['time'] = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")

            for i,shot in enumerate(sequence):
                fname=filename+"_"+ "%02d" % i
                self.capture_image(fname,imgtype,**shot)
                
            # start/stop acquisition have to be outside the capture loop.
            for sens in self._sensors.itervalues():
                sens.cam.stop_acquisition()
                
            if not persist:
                self.stop()        
        except Exception as e:
            self.stop()
            self.logger.error( str(e))
            self.logger.error( traceback.format_exc())
            self.last_run['success'] = False
            self.last_run['error_msg'] = str(e)
            return
        self.logger.info("JAI_AD80GE ran its task")
        self.last_run['success'] = True     
        
    def status(self):
        status= {}
        try:
            if not self._started:   
                self.start()
            for sensor in self._sensors.itervalues():
                sensor_status = OrderedDict()
                sensor_status['Name'] = sensor.name
                sensor_status['Mac'] = sensor.mac

                ipnum=sensor.cam.get_integer_feature("GevCurrentIPAddress")
                o1 = int(ipnum / 16777216) % 256
                o2 = int(ipnum / 65536) % 256
                o3 = int(ipnum / 256) % 256
                o4 = int(ipnum) % 256
                sensor_status["Current IP Addr"]='%(o1)s.%(o2)s.%(o3)s.%(o4)s' % locals()
               
                sensor_status["Camera model"] = sensor.cam.get_model_name()
                sensor_status["Device Version"] = sensor.cam.get_string_feature("DeviceVersion")
                (x,y,w,h) = sensor.cam.get_region()
                mw=sensor.cam.get_integer_feature("WidthMax")
                mh=sensor.cam.get_integer_feature("HeightMax")
                sensor_status["Region size"]= "(%s,%s)" %(w,h)
                sensor_status["Image offset"] = "(%s,%s)" %(x,y)
                sensor_status["Sensor size"]=sensor.cam.get_sensor_size()
                sensor_status["Max size"]= "(%s,%s)" %(mw,mh)
                if sensor.cam.use_exposure_time:
                    sensor_status["Exposure"]=sensor.cam.get_exposure_time()
                else:
                    sensor_status["Exposure"]=sensor.cam.get_integer_feature("ExposureTimeAbs")
                sensor_status["Gain"]=sensor.cam.get_gain()
                sensor_status["Frame rate"]=sensor.cam.get_frame_rate()
                sensor_status["Payload"]=sensor.cam.get_payload()
                sensor_status['SyncMode']=sensor.cam.get_string_feature("SyncMode")
                sensor_status["AcquisitionMode"]=sensor.cam.get_string_feature("AcquisitionMode")
                sensor_status["TriggerSource"]=sensor.cam.get_string_feature("TriggerSource")
                sensor_status["TriggerMode"]=sensor.cam.get_string_feature("TriggerMode")
                sensor_status["Bandwidth"]=sensor.cam.get_integer_feature("StreamBytesPerSecond")
                sensor_status["PixelFormat"]=sensor.cam.get_string_feature("PixelFormat")
                sensor_status["ShutterMode"]=sensor.cam.get_string_feature("ShutterMode")
                sensor_status["PacketSize"]=sensor.cam.get_integer_feature("GevSCPSPacketSize")
                sensor_status["PacketDelay"]=sensor.cam.get_integer_feature("GevSCPD")

                status[sensor.name] = sensor_status  
                
            self.stop()
            
        except Exception as e:
            try:
                self.stop()
            except:
                pass
            self.logger.error( str(e))
            self.logger.error( traceback.format_exc())
            status['Error'] = "Error Encountered:" if str(e)=="" else str(e)
            status['Traceback'] = traceback.format_exc()
            
        return status
        
    def configure(self, **kwargs):
        self.logger.info("Configuration called")
        sensors = kwargs.get('sensors',None)
        if sensors is not None:
            self._sensors = dict()
            self.logger.info("Setting sensors for JAI camera")
            for s in sensors :                
                name =s.get("name", None)
                self._sensors[name] = Sensor(**s)
                self.logger.info("Sensor: %s loaded" %name)
            self.initalized = True 
            
        self._powerdelay = kwargs.get('relay_delay', 15)
        self._powerport = kwargs.get('relay_port', 0)
        relay_name = kwargs.get('relay_name', None)  
        self._powerctlr = None
        if relay_name is not None:
            #TODO what if we're not running under the ais_service?
            self._powerctlr = self.manager.getPluginByName(relay_name, 'Relay').plugin_object
            if self._powerctlr is not None:
                self.logger.info("JAI power controller set to use: %s on port %s with delay %s" 
                    %(relay_name, self._powerport, self._powerdelay))
            else:
                self.logger.error("JAI power controller is not set!")
        if not isinstance(self._powerctlr, Relay):
            self.logger.error("Plugin %s is not available" %relay_name)          
  
    def device_reset(self):
        try:
            if not self._started:   
                self.start()     
            for sensor in self._sensors.itervalues():
                sensor.cam.set_integer_feature("DeviceReset", 1)
        except Exception as e:
            try: 
                self.stop()
            except:
                pass
            self.logger.error( str(e))
            self.logger.error( traceback.format_exc())
              
    def start(self):       
        if not self._started: 
            self.logger.info("JAI_AD80GE is powering up")
            if self._powerctlr is not None:        
                self._power(True)
                self.logger.debug("Power delay for %s seconds" %self._powerdelay)
                time.sleep(self._powerdelay)
                self.logger.debug("Power delay complete, connecting to camera")
            self._ar = Aravis()
            for sens in self._sensors.itervalues():
                self.logger.debug("Getting Handle for Sensor: %s" %sens.name)
                sens.cam = self._ar.get_camera(sens.mac)
                if sens.cam.get_float_feature("ExposureTime") > 0:
                    sens.cam.use_exposure_time = True
                else:
                    sens.cam.use_exposure_time = False
            self.logger.info("JAI_AD80GE started")
            self._started = True       
            
    def stop(self):
        try:
            for sens in self._sensors.itervalues():
                sens.cam.cleanup()
                sens.cam=None
        except:
            for sens in self._sensors.itervalues():
                sens.cam= None
        self._ar = None
        
        if self._powerctlr is not None:        
            self._power( False)
            self.logger.info("JAI_AD80GE is powering down")        
        self._started = False 

    def capture_image(self, name, imgtype="tif", **kwargs):
        if self._started:
            for sensor in self._sensors.itervalues():
                # Setup shot params
                if sensor.cam.use_exposure_time:
                    sensor.cam.set_exposure_time(float(kwargs.get("exposure_time", 33342)))
                else:
                    sensor.cam.set_integer_feature("ExposureTimeAbs", int(kwargs.get("exposure_time", 33342)))
                sensor.cam.set_gain(float(kwargs.get("gain", 0)))
                #max_width,max_height  = sensor.cam.get_sensor_size()
                max_width=sensor.cam.get_integer_feature("WidthMax")
                max_height=sensor.cam.get_integer_feature("HeightMax")
                #Set ROI
                sensor.cam.set_region(kwargs.get("offset_x", 0),
                                      kwargs.get("offset_y", 0),                                      
                                      kwargs.get("width", max_width),
                                      kwargs.get("height", max_height))
                sensor.cam.create_buffers(1)
                                      
            if self._sensors['rgb'].cam.use_exposure_time:
                exp = self._sensors['rgb'].cam.get_exposure_time()
            else:
                exp = self._sensors['rgb'].cam.get_integer_feature("ExposureTimeAbs")        
               
            gain = self._sensors['rgb'].cam.get_gain();                
            self.logger.debug("Jai ExposureTime: %d, GainRaw: %d " % (exp,gain) )

            rgb_status=6 # ARV_BUFFER_STATUS_FILLING
            nir_status=6 # ARV_BUFFER_STATUS_FILLING
            tries=10 #exit out after 10 loops if nothing is complete
            
            # we retry frame grabs if they are incomplete: status will report non-zero for a problem. 
            while ( (rgb_status or nir_status) and tries):             

                self._sensors['rgb'].cam.start_acquisition()
                self._sensors['nir'].cam.start_acquisition()
                self._sensors['rgb'].cam.trigger()                
                rgb_status, rgb_data = self._sensors['rgb'].cam.get_frame()
                nir_status, nir_data = self._sensors['nir'].cam.get_frame()
                tries-=1
                if rgb_status:
                    self.logger.error("Requesting new frame-set. Problem RGB frame. RGB_status: %d" %(rgb_status))    
                if nir_status:
                    self.logger.error("Requesting new frame-set. Problem NIR frame. NIR_status: %d" %(nir_status))
                if tries==0:
                    self.logger.error("Giving up on frame-set. 10 attempts at capturing clean frames.")
            #make our filenames
            rgb_name = name+ "_rgb." + imgtype
            nir_name = name+ "_nir." + imgtype
            # convert bayer color to rgb color
            rgb_data = cv2.cvtColor(rgb_data, cv2.COLOR_BAYER_RG2RGB)
            cv2.imwrite(rgb_name, rgb_data)
            cv2.imwrite(nir_name, nir_data)
 
            self.logger.info("Jai capturing and saving image as: %s"%rgb_name)
            self.logger.info("Jai capturing and saving image as: %s"%nir_name)
            self.last_run['images'].append(rgb_name)  
            self.last_run['images'].append(nir_name)  
        else:
            self.logger.error("JAI_AD80GE is not started")
            raise Exception("JAI Camera is not started.")
              
    def add_sensor(self, name, macaddress):
        kwa = {'name': name, 'mac': macaddress}
        sensor = Sensor(**kwa)
        self._sensors[name] = sensor       

    def __init__(self,**kwargs):
        """Initializes camera instance
        
           Args:
               **kwargs Named arguments to configure the camera(s)
                   Sensors: dict of name: mac address for each of the sensors on board
        """
        super(JAI_AD80GE,self).__init__(**kwargs)
        
        sensors = kwargs.get('sensors', None)
        self._sensors = dict()
        self.last_run = dict()
        self.last_run['success'] = False
        self.last_run['error_msg']= "No run attempted"
        
        #Look for sensor config
        if sensors is not None:
            for s in sensors :
                name =s.get("name", None)
                self._sensors[name] = Sensor(**s)
            self.initalized = True
                      
        self._started = False
        self._powerdelay = kwargs.get('relay_delay', 30)
        self._powerport = kwargs.get('relay_port', 0)
        if 'power_ctlr' in kwargs:
            try:
                self._powerctlr = self._marshal_obj('power_ctlr', **kwargs)
                if not isinstance(self._powerctlr, Relay):
                    raise TypeError
            except:        
                self._powerctlr = None
                self.logger.error("Could not marshall Relay Object")
        elif 'relay_name' in kwargs:
            relay_name = kwargs.get('relay_name', None)
            try:
                self._powerctlr = self.manager.getPluginByName(relay_name, 'Relay').plugin_object
                if not isinstance(self._powerctlr, Relay):
                    self._powerctlr = None
                    self.logger.error("Plugin %s is not a Relay Object" %relay_name)   
            except:
                self.logger.error("Plugin %s is not available" %relay_name)
        else:
            self._powerctlr = None
                                 
    def _gen_filename(self, prefix="jai", dtpattern="%Y-%m-%dT%H%M%S", subdir=None, split=None, nest=False):
        #TODO parse namepattern for timedate pattern?
        #datetime.datetime.now().strftime(dtpattern)
        now = datetime.datetime.now()
        delim = "_"
        #set root path to images
        if self.filestore is None:
            imgpath = "/tmp/jai"
        else:
            imgpath = self.filestore
        #tack on subdir to imgpath if requested    
        if subdir is not None:
            imgpath+="/"+subdir
        #try to make imagepath    
        if not os.path.isdir(imgpath):    
            try:
                os.makedirs(imgpath)
            except OSError:
                if not os.path.isdir(imgpath):
                    self.logger.error("Jai cannot create directory structure for image storage")    
        #if asked to make more subdirs by date do it:            
        if split is not None:
            imgpath = self._split_dir(now,imgpath,split,nest)
        #make datepattern for file name if asked for
        if dtpattern is not None:
            dt = now.strftime(dtpattern)
        else:
            dt=""
            delim=""
        #we return the path and name prefix with dt stamp
        #save_image adds sensor and sequence number and suffix.
        return imgpath+"/"+prefix+delim+dt

    def _split_dir(self, atime, root="/tmp/jai",freq="Daily", nested=False):
        '''
            _split_dir will make a directory structure based on a datetime object
            , frequency, and whether or not it should be nested. 
        '''
        if nested:
            delim="/"
        else:
            delim ="_"
        if freq in ['year', 'Year', 'yearly', 'Yearly']: 
            root+='/'+ str(atime.year)
        elif freq in ['month', 'Month', 'Monthly', 'monthly']:
            root+='/'+str(atime.year)+delim+"%02d"%atime.month    
        elif freq in ['day', 'daily', 'Day', 'Daily']:
            root+='/'+str(atime.year)+delim+"%02d"%atime.month+delim+"%02d"%atime.day  
        elif freq in ['hour', 'hourly', 'Hour', 'Hourly']:
            root+='/'+str(atime.year)+delim+"%02d"%atime.month+delim+"%02d"%atime.day+delim+"%02d"%atime.hour
        if not os.path.isdir(root):    
            try:
                os.makedirs(root)
            except OSError:
                if not os.path.isdir(root):
                    self.logger.error("Jai cannot create directory structure for image storage")
        return root
            
if __name__ == "__main__":
    
    logging.basicConfig(level=logging.DEBUG)
    
    init_args = {
        "sensors":(
            {"name": "rgb", "mac": "00:0c:df:04:93:94"},
            {"name": "nir", "mac": "00:0c:df:04:a3:94"}        
        ),
        "power_ctlr":{
            'class': "Phidget",
            'module': 'ais.plugins.phidget.phidget'
        },
        'relay_delay': 30,
        'relay_port':0
    }    
    
    run_args = {
        'pixel_formats':(
            {'sensor':'rgb', 'pixel_format': 'BayerRG8'},
            {'sensor':'nir', 'pixel_format': 'Mono8'}        
        ),
        'file_prefix': 'hdr',
        'sequence':[
            {'exposure_time': 20},
            {'exposure_time': 40},
            {'exposure_time': 120},
            {'exposure_time': 240},
            {'exposure_time': 480},
            {'exposure_time': 960},
            {'exposure_time': 1920},
            {'exposure_time': 3840},
            {'exposure_time': 7680},
            {'exposure_time': 15360},
            {'exposure_time': 30720},
        ]
    }    
    
    jai = JAI_AD80GE(**init_args)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(jai.status())
    #jai.run(**run_args)
    