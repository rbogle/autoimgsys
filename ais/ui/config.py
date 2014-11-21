import os

DEBUG=True
# Create in-memory database
DATABASE_FILE='ais_db.sqlite'
DATABASE_PATH = '/db/'
DATABASE_PREFIX = 'sqlite:///'
SQLALCHEMY_DATABASE_URI=""

SQLALCHEMY_ECHO = False

SECRET_KEY = os.urandom(24)

FILESTORE = '/mnt/data'