from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy


import config 

flask = Flask('ais')
flask.template_folder = flask.root_path
flask.static_folder = flask.root_path+"/ui/static"

config.DATABASE_PATH = flask.root_path+config.DATABASE_PATH
config.SQLALCHEMY_DATABASE_URI=config.DATABASE_PREFIX+config.DATABASE_PATH+config.DATABASE_FILE
flask.config.from_object(config)
 
db = SQLAlchemy(flask)

from views import *
from models import *
