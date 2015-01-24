import datetime
from ais.ui import db
#from sqlalchemy import Column, Integer, String, PickleType, DateTime, Boolean, ForeignKey
#from sqlalchemy.orm import relationship, backref

# Create user model.


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    def __repr__(self):
        return '<User %s>' % self.login

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True) # auto incrementing
    plugin_id = db.Column(db.Integer, db.ForeignKey('plugin.id'))
    plugin = db.relationship('Plugin')
    code = db.Column(db.String) # 
    msg = db.Column(db.String)
    trace = db.Column(db.String)
    datetime = db.Column(db.DateTime, default=datetime.datetime.now()) # the current timestamp     
        
class Log(db.Model):
    __bind_key__ = 'logs'
    id = db.Column(db.Integer, primary_key=True) # auto incrementing
    logger = db.Column(db.String) # the name of the logger. (e.g. myapp.views)
    module = db.Column(db.String)
    level = db.Column(db.String) # info, debug, or error?
    trace = db.Column(db.String) # the full traceback printout
    msg = db.Column(db.String) # any custom log you may have included
    created = db.Column(db.DateTime, default=datetime.datetime.now()) # the current timestamp       

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    year = db.Column(db.String(10))
    month = db.Column(db.String(10))
    day = db.Column(db.String(10))
    week = db.Column(db.String(10))
    day_of_week = db.Column(db.String(10))
    hour= db.Column(db.String(10))
    minute = db.Column(db.String(10))
    second = db.Column(db.String(10))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    def get_args(self):
        args = dict()
        keepterms = [
            'year', 'month', 'day', 
            'week', 'day_of_week', 'hour',
            'minute', 'second', 'start_date', 'end_date'            
            ]
        for k,v in self.__dict__.iteritems():
            if k in keepterms:            
                args[k]=v
        return args
        
    def __repr__(self):
        return self.name
    
class Plugin(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(100))
    class_name = db.Column(db.String(100))
    enabled = db.Column(db.Boolean, default=False)
    args = db.Column(db.PickleType)
    
    def __repr__(self):
        return self.name
        
        
class Auditor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100),nullable=False, unique=True)
    plugin_id = db.Column(db.Integer, db.ForeignKey('plugin.id'))
    plugin = db.relationship('Plugin')
    event_mask = db.Column(db.Integer)
    enabled = db.Column(db.Boolean)
    
    def __repr__(self):
        return self.name
        
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)   
    name = db.Column(db.String(100), nullable=False, unique=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    schedule = db.relationship("Schedule")
    config_id = db.Column(db.Integer, db.ForeignKey('config.id'))
    config = db.relationship("Config")
    enabled = db.Column(db.Boolean)
    running = db.Column(db.Boolean)
    
    def __repr__(self):
        return self.name
        
class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    plugin_id = db.Column(db.Integer, db.ForeignKey('plugin.id'))
    plugin = db.relationship('Plugin')
    role = db.Column(db.Enum('Initalize', 'Runtime', name='config_roles'))
    args = db.Column(db.PickleType)
    
    def __repr__(self):
        return "%s --> %s" %(self.plugin.name,self.name)