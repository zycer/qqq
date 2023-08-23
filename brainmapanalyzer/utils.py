#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
from baselib.utils import attrdict, ListProxy, DictProxy
import json
from dateutil.parser import parse
from datetime import datetime, date


def findField(obj, path_list):
    '''从字典中提取字段
        
    
    Args:
        obj (dict): 
        path_list (list): 分级字段列表
    
    Raises:
        ValueError: [description]
    
    Returns:
        list: 所有提取到的值, 如果路径中有一级或多级是数组,则会返回超过1个值
    '''
    if isinstance(path_list, str):
        path_list = path_list.split('.')
    if not path_list:
        if isinstance(obj, list):
            return obj
        else:
            return [obj]
    result = []
    fd = path_list[0]
    if isinstance(obj, (DictProxy, ListProxy)):
        obj = obj.obj
    if isinstance(obj, str):
        obj = json.loads(obj)
    
    if isinstance(obj, dict):
        if fd in obj:
            result.extend(findField(obj[fd], path_list[1:]))
    elif isinstance(obj, list):
        for item in obj:
            result.extend(findField(item, path_list))
    else:
        raise ValueError('cannot extract field [%s]from type(%s)' % ('.'.join(path_list), type(obj)))
    return result

def findOneField(obj, path_list):
    ret = findField(obj, path_list)
    if ret:
        return ret[0]
    else:
        return None

def parseTime(s) -> datetime:
    if isinstance(s, datetime):
        return s
    else:
        return parse(s).replace(tzinfo=None) # type: ignore

def parseDate(s) -> date:
    if isinstance(s, datetime):
        return s.date()
    else:
        return parse(s).replace(tzinfo=None).date() # type: ignore
