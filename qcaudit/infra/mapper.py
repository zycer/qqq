#!/usr/bin/env python3
#coding=utf8
"""
# Author: f
# Created Time : Mon 21 Sep 2015 09:12:22 PM CST

# File Name: datafield.py
# Description:

"""

import string
import logging
import json
import datetime
from typing import Any, Dict, Type
import decimal

NO_VALUE = object()

class TableMapper(object):
    """定义mysql表结构与数据源结构之间的映射关系
    """

    def __init__(self, model, **kwargs):
        self._model = model
        self._field_mappers = {}
        self.bindMany(**kwargs)
    
    def bindMany(self, **kwargs):
        """一次添加多个字段的对应关系
        """
        for key, value in kwargs.items():
            if isinstance(value, (str, list, tuple)) or callable(value):
                self._field_mappers[key] = FieldMapper(value)
            else:
                self._field_mappers[key] = value
        # 支持链式调用
        return self

    def bind(self, key, cands, delNull=True, allowException = True, 
                    default = None, force = NO_VALUE, postFunc=None, preFunc=None, 
                    range=None, options=None, strip=True):
        """为一个目标字段设置映射关系, 参数与FieldMapper对应
        """
        self._field_mappers[key] = FieldMapper(cands=cands, delNull=delNull, 
                            allowException=allowException, default=default, 
                            force=force, postFunc=postFunc, preFunc=preFunc,
                            range=range, options=options, strip=strip)
        # 支持链式调用
        return self    
    
    def getColumnType(self, column: str):
        """获取列的类型

        Args:
            column (str): 列名
        """
        col = self._model.__table__.columns._data.get(column)
        return col.type.python_type
    
    def columns(self):
        """得到所有的列"""
        #print(list(self._model.__table__.columns.keys()))
        #print(list(self._model.__table__.columns.values()))
        for item in self._model.__table__.columns.keys():
            yield item

    def map(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换一个dict到目标的model, 如果涉及到多表关联, 应该事先将目标数据结构组织成一个dict

        Args:
            data (Dict[str, Any]): 一个json字典

        Returns:
            Dict[str, Any]: [description]
        """
        result = {}
        for k in self.columns():
            fieldMapper = self._field_mappers.get(k)
            if not fieldMapper:
                #print(f'{k} has no mapper')
                continue
            value = fieldMapper.map(data, self.getColumnType(k))
            if value is NO_VALUE:
                continue
            else:
                result[k] = value
        return result

class FieldMapper(object):
    def __init__(self, cands=None, delNull=True, allowException = True, 
                    default = None, force = NO_VALUE, postFunc=None, preFunc=None, 
                    range=None, options=None, strip=True):
        # 候选字段, 可以有多个, 按顺序找到一个就结束
        if isinstance(cands, str) or callable(cands):
            self.cands = [cands]
        else:
            self.cands = cands or []
        # None时是否需要值, 实际上最终model会当做Null处理
        self.delNull = delNull
        # 预处理函数, 在进行映射之前执行
        self.preFunc = preFunc
        #后处理函数, 在映射完成之后执行
        self.postFunc = postFunc
        # 默认值, 当找不到候选字段, 最终计算值为None时使用
        self.default = default
        # 不进行字段映射, 直接强制设置值
        self.force = force
        # 值的取值范围, 如果不在取值范围则为None
        self.range = range
        # 是否允许映射转换异常, 允许的话,异常时使用默认值
        self.allowException = allowException

        #当字段是枚举类型时,枚举值的可取范围
        self.options = options

        #当字段是字符串类型时,是否删除左右空格
        self.strip = strip
    
    def typeConvert(self, value: Any, valueType: Type, default=None):
        """将变量转换成对应的类型

        Args:
            value (Any): 变量值
            valueType (Type): 目标类型
        """
        if isinstance(value, valueType):
            return value
        if value is None:
            return None
        # 字符串强制转换返回
        if valueType is str or valueType is decimal.Decimal:
            return str(value)
        # 数值型强制转换
        if valueType is int or valueType is float:
            return valueType(value)
        # 日期时间使用标准格式转换, 转换失败设置成null
        if isinstance(value, str):
            if valueType is datetime.datetime:
                try:
                    return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logging.exception(e)
                    return None
            elif valueType is datetime.date:
                try:
                    return datetime.datetime.strptime(value, '%Y-%m-%d')
                except Exception as e:
                    logging.exception(e)
                    return None           

        # 放弃转换
        return value

    def map(self, data: dict, valueType: Type):
        """从字典中找到一个候选值, 并转换成目标类型

        Args:
            data (dict): [description]
            valueType (Type): [description]
        """
        found = False
        candValue = None
        if self.force is not NO_VALUE:
            return self.force
        for candKey in self.cands:
            if candKey in data:
                found = True
                candValue = data[candKey]
            elif callable(candKey):
                found = True
                candValue = candKey(data)
            else:
                continue
            if self.preFunc:
                candValue = self.preFunc(candValue)
            try:
                candValue = self.typeConvert(candValue, valueType)
            except Exception as e:
                if self.allowException:
                    logging.exception(e)
                    logging.info(f'parse {data[candKey]} to {valueType} failed')
                    candValue = self.default
                else:
                    raise e
            if self.postFunc:
                candValue = self.postFunc(candValue)
            break
        if not found:
            candValue = self.default
        else:
            if self.options and candValue not in self.options:
                logging.info('{candValue} not in options, set to default')
                candValue = self.default
            elif self.range and (candValue <= self.range[0] or candValue > self.range[1]):
                logging.info('{candValue} not in range, set to default')
                candValue = self.default
        if isinstance(candValue, str) and self.strip:
            candValue = candValue.strip()
        if candValue is None and self.delNull:
            return NO_VALUE
        else:
            return candValue


if __name__ == '__main__':
    from qcetl.models.dbmodels import Case
    mapper = TableMapper(Case, caseId=['admission_no'],
            patientId='patient_no',
            visitTimes='in_times',
            orgCode='hosp_id',
            name='patient_name',
            gender='gender_code',
            age='age',
            ageUnit='ageUnit',
            department='in_dept_name',
            departmentId='in_dept_code',
            attendDoctor='doctor_name',
            attendCode='doctor_code',
            admitTime='in_date',
            dischargeTime='out_date',
            status=FieldMapper(force=1),
            isDead='dead_flag',
            hospital='溧水人民医院',
            branch='溧水人民医院',
            diagnosis='in_diag',
            outDeptId='out_dept_code',
            outDeptName='out_dept_name',
            caseType=FieldMapper(force='2')
        )
    row = {'admission_no': 'ZY010000600149', 'patient_no': '0000600149', 'in_times': 1, 'hosp_id': '426070487', 'patient_name': '黄秋瑾', 'gender_code': '女', 'birth_date': datetime.datetime(1983, 12, 27, 0, 0), 'age': 38, 'in_dept_code': '3009', 'in_dept_name': '产科', 'out_dept_code': '3009', 'out_dept_name': '产科', 'in_date': datetime.datetime(2021, 3, 18, 2, 9, 13), 'out_date': datetime.datetime(2021, 3, 23, 9, 31, 57), 'in_diag': '胎膜早破', 'dead_flag': 0, 'doctor_code': '00627', 'doctor_name': '潘格格', 'rn': 1, 'ageUnit': '岁'}
    after = mapper.map(row)
    print(after)