#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import json
from baselib.utils import attrdict
from collections import defaultdict
import logging


class DataSet:
    """用来表示数据库中的一组表的数据
       self._data的key是表名, value是表中每一行数据对应的dict的list
    """

    def __init__(self):
        self._data = defaultdict(list)
    
    def add(self, rows, tablename):
        '''增加一条或多条数据
        '''
        if isinstance(rows, (str, bytes)):
            value = json.loads(rows)
        else:
            value = rows
        if isinstance(value, list):
            for row in value:
                self._data[tablename].append(attrdict(row))
        else:
            self._data[tablename].append(attrdict(value))
    
    
    def iterrows(self, tablename=None):
        '''遍历所有数据
        '''
        if tablename:
            for row in self._data.get(tablename, []):
                yield tablename, row
        else:
            for table, rows in self._data.items():
                for row in rows:
                    yield table, row
        