from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

from ais import __version__
import config 

flask = Flask('ais')
flask.template_folder = flask.root_path
#flask.static_folder = flask.root_path+"/static"

config.DATABASE_PATH = flask.root_path+config.DATABASE_PATH
config.SQLALCHEMY_DATABASE_URI=config.DATABASE_PREFIX+config.DATABASE_PATH+config.APP_DATABASE_FILE
config.SQLALCHEMY_BINDS= {
    'logs': config.DATABASE_PREFIX+config.DATABASE_PATH+config.LOG_DATABASE_FILE
}
flask.config.from_object(config)
 
db = SQLAlchemy(flask)

from views import *
from models import *
