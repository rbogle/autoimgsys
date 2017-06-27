# Automated Imaging System (AIS)

USGS Automated Imaging System (AIS) is a python based webserver which enables  scheduling and control of automated image capture from imaging devices attached via GigE, USB, or IP protocols. More generically it can be used to schedule any data collection via sensors attached to the system. 

Its meant to be deployed on SBC linux systems. Linux OS customization/configuration is up to the user. Typical configuration includes providing wifi AP for UI connectivity, GPS based clock, USB cellular modem for data uploads, Phidget USB controlled relays for device power control, POE for device power and comms. Future project work is to provide an ansible playbook to configure a minimal ubuntu install. 

Fundamentally this is a python based task scheduler, constructed to see Modules (plugins) as potential tasks to be executed based upon a chron like schedule. Modules can be written to perform any action, but typically are hardware drivers for external sensors e.g. cameras. We have two camera modules: one for a JAI dual CCD GigE camera, and one for an AST single CCD GigE camera. Additional modules include drivers for Phidget based boards, data synchronization, and basic system control. Each module provides its own interface to the UI.

## Front Page:
![](https://cloud.githubusercontent.com/assets/7741121/24219947/d9e8f0a4-0f05-11e7-9543-dff0e0e91f43.png)

## Tasks:
![](https://cloud.githubusercontent.com/assets/7741121/24219952/de9de5aa-0f05-11e7-80c6-c32ece04695f.png)

## Schedules:
![](https://cloud.githubusercontent.com/assets/7741121/24219956/e1df71a2-0f05-11e7-883c-6b9b5eaecfe9.png)

## Data File Browsing:
![](https://cloud.githubusercontent.com/assets/7741121/24219960/e66b2888-0f05-11e7-8b36-6ef7b162ca1c.png)

## Data-Sync Module:
### Real-time sync
![](https://cloud.githubusercontent.com/assets/7741121/24219961/e6850e42-0f05-11e7-8d38-5c552fab4854.png)

### One time sync
![](https://cloud.githubusercontent.com/assets/7741121/24219969/ec5e0e9a-0f05-11e7-8e46-87320ef40270.png)

### Scheduled Sync
![](https://cloud.githubusercontent.com/assets/7741121/24219971/ec610456-0f05-11e7-8222-a5b921b69619.png)

## System Module:
### main functions
![](https://cloud.githubusercontent.com/assets/7741121/24219962/e6891442-0f05-11e7-9c3b-0db292076027.png)

### disk/partition mounting
![](https://cloud.githubusercontent.com/assets/7741121/24219970/ec5ee1da-0f05-11e7-8603-2620bcea089b.png)

## PhenoCam Module:
### main functions
![](https://cloud.githubusercontent.com/assets/7741121/24219973/f05fce70-0f05-11e7-8987-16b6afb94de2.png)

### device setup
![](https://cloud.githubusercontent.com/assets/7741121/24219981/f5cc7aac-0f05-11e7-93a7-3759579c7282.png)

### image capture config
![](https://cloud.githubusercontent.com/assets/7741121/24219982/f5e14d74-0f05-11e7-94af-4d4b5cb6cd48.png)

## Admin->Module Logs:
![](https://cloud.githubusercontent.com/assets/7741121/24219984/f5ea48ac-0f05-11e7-806e-20908c767222.png)
