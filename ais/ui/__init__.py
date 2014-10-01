from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy


import config 

flask = Flask('ais')
flask.template_folder = flask.root_path
flask.static_folder = flask.root_path+"/ui/static"
flask.config.from_object(config)
 
db = SQLAlchemy(flask)

from views import *
from models import *
