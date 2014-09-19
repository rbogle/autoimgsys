from flask.ext.sqlalchemy import SQLAlchemy
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
        

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    year = db.Column(db.String(10))
    month = db.Column(db.String(10))
    day = db.Column(db.String(10))
    week = db.Column(db.String(10))
    dayofweek = db.Column(db.String(10))
    hour= db.Column(db.String(10))
    minute = db.Column(db.String(10))
    second = db.Column(db.String(10))
    startdate = db.Column(db.DateTime)
    enddate = db.Column(db.DateTime)
    #jobs = db.relationship('Job')
    
    def __repr__(self):
        return '<Schedule %s>' % self.name
    
class Plugin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    class_name = db.Column(db.String(100))
    module_name = db.Column(db.String(100))
    args = db.Column(db.PickleType)
    #actions = db.relationship('Action')
    #reactions = db.relationship('Reaction')
    def __repr__(self):
        return '<Plugin %s>' % self.name
        
class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    args = db.Column(db.PickleType)
    plugin_id = db.Column(db.Integer, db.ForeignKey('plugin.id'))
    plugin = db.relationship('Plugin')
    
    def __repr__(self):
        return '<Action %s>' % self.name
        
class Auditor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    plugin_id = db.Column(db.Integer, db.ForeignKey('plugin.id'))
    plugin = db.relationship('Plugin')
    event_mask = db.Column(db.Integer)
    enabled = db.Column(db.Boolean)
    
    def __repr__(self):
        return '<Reaction %s>' % self.name
        
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)   
    name = db.Column(db.String(100))
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    schedule = db.relationship("Schedule")
    action_id = db.Column(db.Integer, db.ForeignKey('action.id'))
    action = db.relationship("Action")
    enabled = db.Column(db.Boolean)
    
    def __repr__(self):
        return '<Job: %s>' % self.name
    