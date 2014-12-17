# -*- coding: utf-8 -*-
import logging
import datetime
import traceback

#import transaction
from ais.ui import db
from ais.ui.models import Log

class SQLAlchemyHandler(logging.Handler):
    # A very basic logger that commits a LogRecord to the SQL Db
    def emit(self, record):
        trace = None
        exc = record.__dict__['exc_info']
        if exc:
            trace = traceback.format_exc(exc)
        log = Log(
            logger=record.__dict__['name'],
            module = record.__dict__['module'],
            level=record.__dict__['levelname'],
            trace=trace,
            created = datetime.datetime.fromtimestamp(record.__dict__['created']),
            msg=record.__dict__['msg'])
        db.session.add(log)
        db.session.commit()
