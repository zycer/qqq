#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-02-15 09:19:23

'''
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List
import brainmapanalyzer.keywords.operators as opers
import logging
# from iyoudoctor.hosp.search.data_pb2 import ValueConstraint as PBValueConstraint
# from iyoudoctor.hosp.search.data_pb2 import CommonKeyword as PBKeyword
# from google.protobuf.json_format import MessageToDict, ParseDict
from uuid import uuid4

class Keyword:
    """关键词基类, 对于所有的关键词可以抽象为数据库中某一个表对应的某一个字段
    """
    FIELD_TYPE_INT = 'integer'
    FIELD_TYPE_FLOAT = 'float'
    FIELD_TYPE_STRING = 'string'
    FIELD_TYPE_DATETIME = 'datetime'
    FIELD_TYPE_BOOL = 'boolean'
    # 目前只支持字符串的list, 所以list与字符串是相同的
    FIELD_TYPE_LIST = 'list'
    
    # 用于检索关系型数据库字段的关键词类型, json数据一样
    KWORD_RDB_FIELD = 'rdb_field'
    
    def __init__(self, tablename: str, field: str, 
                 fieldtype: str='string', operators=[], fieldName='',
                 min=None, max=None,
                 unit=None,
                 choices: List[str]=[],
                 enableSug=False,
                 unitChoices: List[str]=[], 
                 children=[], 
                 kwordId='',
                 id=None,
                 type='',
                 category='',
                 subCategory='',
                 defaultValue: List[str]=[],
                 defaultOperator=None
                 ):
        # 表名
        self.tablename = tablename
        # 字段名
        self.field = field
        # 字段的描述, 用于界面展示
        self.fieldName = fieldName or field
        # 字段类型, 已经转换成整数/浮点数/字符串/时间/布尔这几种类型
        self.fieldtype = fieldtype or 'string'
        # 所有可能的运算符
        self.operators = []
        if operators:
            for op in self.getAllowedOperators():
                if op.Id in operators:
                    self.operators.append(op)
        else:
            # 字符串默认不允许大于和小于操作
            self.operators = self.getAllowedOperators()
            if self.fieldtype == 'string':
                self.operators = [
                    op for op in self.operators if op.Id not in ('gt', 'lt')
                ]

        # 关键词id, 可用于定义不同的关键词解析器, 实际上是关键词类型
        self.kwordId = kwordId or self.KWORD_RDB_FIELD
        # 子关键词
        self.children = children
        # 关键词id, 仅用于前端区分不同关键词, 可使用数据库自增id
        self.id = str(id) if id else str(uuid4())
        # 类型（例如：基本信息，疾病、症状、化验等）
        self.type = type
        # 一级分类/二级分类
        self.category = category
        self.subCategory = subCategory
        # 默认值
        self.defaultValue = defaultValue
        # 默认操作符
        self.defaultOperator = defaultOperator
        # 值约束    
        self.valueConstraint = ValueConstraint(
            # list只支持字符串的数组, 对前端处理方式一样
            type=self.FIELD_TYPE_STRING if self.fieldtype == self.FIELD_TYPE_LIST else self.fieldtype,
            operators=self.operators,
            min=min,
            max=max,
            unit=unit,
            choices=choices,
            enableSug=enableSug,
            unitChoices=unitChoices
        )
        
    def getOperator(self, op) -> opers.Operator:
        for operator in self.operators:
            if operator._id == op:
                return operator
        return None # type: ignore
    
    def getAllowedOperators(self):
        """基于字段类型获取运算符
        """
        if self.fieldtype == self.FIELD_TYPE_INT:
            return [
                opers.eqNumOperator, opers.gteNumOperator, opers.gtNumOperator,
                opers.lteNumOperator, opers.ltNumOperator, opers.neNumOperator
            ]
        elif self.fieldtype == self.FIELD_TYPE_FLOAT:
            return [
                opers.gtNumOperator, opers.ltNumOperator
            ]
        elif self.fieldtype == self.FIELD_TYPE_STRING:
            return [
                # 等于
                opers.eqStrOperator,
                # 包含
                opers.includeStrOperator,
                # 不包含
                opers.excludeStrOperator,
                # 正则表达式
                opers.regexStrOperator,
                # 不等于
                opers.neStrOperator,
                # 大于, 仅当字符串可强制转换为数字时使用
                opers.gtNumOperator,
                # 小于, 仅当字符串可强制转换为数字时使用
                opers.ltNumOperator
            ]
        elif self.fieldtype == self.FIELD_TYPE_DATETIME:
            return [
                opers.eqTimeOperator, opers.bwTimeOperator,
                opers.lteTimeOperator, opers.ltTimeOperator,
                opers.gteTimeOperator, opers.gtTimeOperator,
            ]
        elif self.fieldtype == self.FIELD_TYPE_BOOL:
            return [
                opers.eqNumOperator
            ]
        elif self.fieldtype == self.FIELD_TYPE_LIST:
            return [
                opers.includeStrOperator, opers.excludeStrOperator
            ]
        else:
            return [
                opers.eqStrOperator, opers.neStrOperator
            ]
            
    def asJson(self):
        """转换成json, 与proto定义的结构一致"""
        js: Dict[str, Any] = {
            'id': self.id,
            'kwordId': self.kwordId,
            'type': self.type,
            'name': self.field,
            'displayName': self.fieldName,
            'params': {
                'tablename': self.tablename,
                'field': self.field,
                'fieldtype': self.fieldtype
            },
            'valueConstraint': self.valueConstraint.asJson(),
            'children': [child.asJson() for child in self.children],
        }
        if self.category:
            js['category'] = self.category
        if self.subCategory:
            js['subCategory'] = self.subCategory
        if self.defaultValue:
            js['defaultValue'] = self.defaultValue
        if self.defaultOperator:
            js['defaultOperator'] = self.defaultOperator
        return js
    
    def asProto(self):
        """生成proto中定义的结构, 用于接口给前端返回
        """
        # p = PBKeyword()
        # ParseDict(self.asJson(), p) # type: ignore
        # return p
        return self.asJson()
    
    @classmethod
    def fromModel(cls, row):
        """从KeywordModel表中的字段生成, 此表在各个项目中名字可能不一样, 或许会增加字段, 但需要保证公共字段一致
        """
        kword = Keyword(
            tablename=row.table_name,
            fieldName=row.name,
            field=row.field,
            operators=row.operators.split(',') if row.operators else [],
            min=row.min_value,
            max=row.max_value,
            unit=row.unit,
            choices=row.choices.split(',') if row.choices else [],
            enableSug=True if row.enableSug else False,
            kwordId=row.kword_id,
            category=row.category,
            type=row.type,
            subCategory=row.sub_category,
            defaultValue=row.default_value.split(',') if row.default_value else [],
            defaultOperator=row.default_operator,
            id=row.id,
            fieldtype=row.fieldtype
        )
        return kword
        
    @classmethod
    def fromModels(cls, rows, groupSameTable=False, ignoreGroupTables=[]):    
        """将全部指标一起加载后处理

        Args:
            rows (list): 从数据库中读取到的所有行
            groupSameTable (bool, optional): 将表名相同的指标放到关联属性中, 不跨表查询时不需要. Defaults to False.
            ignoreGroupTables (list): 哪些表不需要生成关联属性
        Returns:
            list
        """
        kwordsByTable = defaultdict(list)
        for row in rows:
            kword = cls.fromModel(row)
            kwordsByTable[row.table_name].append(kword)
        
        result = []
        for table, kwords in kwordsByTable.items():
            if groupSameTable and table not in ignoreGroupTables:
                for kw in kwords:
                    tmp = deepcopy(kw)
                    tmp.children = kwords
                    result.append(tmp)
            else:
                result.extend(kwords)
        return result

class ValueConstraint:
    """关键词的值约束
    """
    def __init__(self, type: str, operators: List[opers.Operator],
                 min=None, max=None,
                 unit=None,
                 choices: List[str]=[],
                 enableSug=False,
                 unitChoices: List[str]=[]
                 ):
        # 字段类型
        self.type = type
        # 数值类型的最小值
        self.min = min
        # 数值类型的最大值
        self.max = max
        # 单位
        self.unit = unit
        # 可选项
        self.choices = choices
        # 运算符
        self.operators = operators
        # 是否启用sug搜索, 将搜索相同kword的其他可选项
        self.enableSug = enableSug
        # 单位可选项
        self.unitChoices = unitChoices
    
    def asJson(self):
        js: Dict[str, Any] = {
            'type': self.type
        }    
        if self.min is not None:
            js['min'] = self.min
        if self.max is not None:
            js['max'] = self.max
        if self.unit is not None:
            js['min'] = self.min
        if self.unitChoices:
            js['unitChoices'] = self.unitChoices
        if self.enableSug:
            js['enableSug'] = self.enableSug
        if self.operators:
            js['operators'] = [
                {
                    'id': op._id,
                    'operand': op.operand,
                    'text': op.text,
                    'tip': op.tip
                } for op in self.operators
            ]
        if self.choices:
            js["choices"] = self.choices
        return js
        