import os

DEBUG=True
# Create in-memory database
DATABASE_FILE='ais_db.sqlite'
DATABASE_PATH = os.getcwd()+'/ais/db/'
DATABASE_PREFIX = 'sqlite:///'
SQLALCHEMY_DATABASE_URI=DATABASE_PREFIX+DATABASE_PATH+DATABASE_FILE
SQLALCHEMY_ECHO = False

SECRET_KEY = os.urandom(24)