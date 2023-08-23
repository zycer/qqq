#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 17:45:22

'''

import datetime
import logging
from typing import Callable
from sqlalchemy.ext.declarative import DeclarativeMeta
import json
import time
from google.protobuf.json_format import ParseDict, Parse, MessageToDict

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
        # elif isinstance(obj, Pagination):
        #     return self.default(obj.items)
        return json.JSONEncoder.default(self, obj)

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class ModelUtil(object):

    @classmethod
    def asDict(cls, row, with_table_name=False, with_patient_id=False):
        data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        if with_table_name:
            data['_yida_table_name'] = row.__table__.name
        if with_patient_id and 'patientId' in data:
            data['_yida_patient_id'] = data['patientId']
        return AttrDict(**data)
    
    @classmethod
    def asJson(cls, row, with_table_name=False, with_patient_id=False):
        return json.dumps(cls.asDict(row),cls=SqlAlchemyEncoder, ensure_ascii=False)

class ModelProtoUtil(object):

    @classmethod
    def modelToProto(cls, row, proto, keyList, keyMap):
        data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        modelDict = AttrDict(**data)
        resultDict = {}
        for key in keyList:
            resultDict[key] = modelDict[key]
        for mKey, pKey in keyMap.items():
            if isinstance(modelDict.get(mKey), datetime.datetime):
                resultDict[pKey] = modelDict.get(mKey).strftime("%Y-%m-%d %H:%M:%S ")
            else:
                resultDict[pKey] = modelDict.get(mKey)

        ParseDict(resultDict, proto, ignore_unknown_fields = True)

        return proto
    