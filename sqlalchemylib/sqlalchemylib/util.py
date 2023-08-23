#!/usr/bin/env python
# coding=utf-8
import datetime
import logging
from sqlalchemy.ext.declarative import DeclarativeMeta
import json
import time

class SqlAlchemyEncoder(json.JSONEncoder):
    
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj.__class__, DeclarativeMeta):
            return self.default({i.name: getattr(obj, i.name) for i in obj.__table__.columns})
        elif isinstance(obj, dict):
            for k in obj:
                try:
                    if isinstance(obj[k], (datetime.datetime, datetime.date, DeclarativeMeta)):
                        obj[k] = self.default(obj[k])
                    else:
                        obj[k] = obj[k]
                except TypeError:
                    obj[k] = None
            return obj
        else:
            return str(obj)
        # elif isinstance(obj, Pagination):
        #     return self.default(obj.items)
        return json.JSONEncoder.default(self, obj)

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class ModelUtil(object):

    @classmethod
    def asDict(cls, row, with_table_name=False):
        data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        if with_table_name:
            data['_yida_table_name'] = row.__table__.name
        return AttrDict(**data)
    
    @classmethod
    def asJson(cls, row, with_table_name=False):
        return json.dumps(cls.asDict(row, with_table_name=with_table_name),cls=SqlAlchemyEncoder, ensure_ascii=False)


def logtime(func):
    """output time cost of function
    """    
    def wrapper(*args, **kwargs):
        startTime = time.time()
        ret = func(*args, **kwargs)
        endTime = time.time()
        costTime = endTime - startTime
        logging.info('%s, args: %s, kwargs: %s, Cost: %0.2f s', func.__name__, args, kwargs, costTime)
        return ret
    return wrapper

