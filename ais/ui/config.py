import os,socket

DEBUG=True
USE_RELOADER=False
# Create in-memory database
APP_DATABASE_FILE='app_db.sqlite'
LOG_DATABASE_FILE='log_db.sqlite'
DATABASE_PATH = '/db/'
DATABASE_PREFIX = 'sqlite:///'

#SQLALCHEMY_DATABASE_URI=""

SQLALCHEMY_ECHO = False

HOSTNAME = socket.gethostname()

SECRET_KEY = os.urandom(24)

FILESTORE = '/mnt/data' #where module mount their data directories
DISKSTORE = '/mnt' # where disks can be mounted. 

LOGGING = {
    'version':1,
    'disable_existing_loggers': True,
    'formatters': {
        'default':  {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'console':{
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
    },
    'root': {
        'level': 'DEBUG', 
        'handlers': ['console']
    }
    
}