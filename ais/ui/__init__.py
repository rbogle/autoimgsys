from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy


import config 

flask = Flask('ais')
flask.template_folder = flask.root_path
flask.config.from_object(config)
#flask.config['SQLALCHEMY_DATABASE_URI']=config.DATABASE_PREFIX+config.DATABASE_PATH+config.DATABASE_FILE
db = SQLAlchemy(flask)

from views import *
from models import *
