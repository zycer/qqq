#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 20:13:19

'''
from dataclasses import dataclass, field
from typing import List
import arrow
from sqlalchemy import text

from qcaudit.common.const import AUDIT_TYPE_ACTIVE


@dataclass
class Page():
	# 开始
	start: int = 0
	# 条数
	size: int = 10
 
@dataclass
class SortField(object):
    # 排序字段
    field: str
    # 升序/降序
    way: str = "DESC"
    # 字段所在的表名, 单表查询可以不指定, 多表查询必须指定
    table: str = ''
    # 数组格式的排序详情
    extParams: list = None

    def apply(self, query, model=None):
        """将排序规则应用到query上
        """
        order_by_field_str = ""
        # null_in_frist_str = "IF(ISNULL(dischargeTime),0,1),"
        if self.extParams:
            # 问题数量/重点病例排序需要读具体排序详情
            if "problemcount" in self.field.lower():
                if self.extParams[0] == "问题多":
                    self.way = "desc"
                order_by_field_str = f'{self.field} {self.way}'
            if "tags" == self.field.lower():
                self.way = "desc"
                for tag in self.extParams:
                    order_by_field_str += '''instr(%s, "%s") %s, ''' % (self.field, tag, self.way)
                order_by_field_str = order_by_field_str[:-2]
        if model is not None:
            column = getattr(model, self.field)
            if self.way.lower() == 'desc':
                return query.order_by(column.desc())
            else:
                return query.order_by(column.asc())
        else:
            if not order_by_field_str:
                # order_by_field_str = f'{null_in_frist_str} {self.field} {self.way}'
                order_by_field_str = f'{self.field} {self.way}'
            return query.order_by(text(order_by_field_str))


@dataclass
class ListRequestBase(object):

    start: int = 0
    size: int = 10
    is_export: int = 0
    sortFields: List[SortField] = field(default_factory=list)

    def applySort(self, query, connection):
        """应用排序规则"""
        for field in self.sortFields:
            if field.table and self.auditType != AUDIT_TYPE_ACTIVE:
                model = connection[field.table]
            else:
                model = None
            query = field.apply(query, model)
        return query

    def applyPageSize(self, query, connection):
        """应用翻页参数"""
        return query.slice(self.start, self.start+self.size)
    
    def validate(self):
        if self.start < 0:
            self.start = 0
        if self.size <= 0:
            self.size = 10
    
    def applyFilter(self, query, connection):
        """应用过滤条件到query上, 返回一个新的query

        Args:
            query ([type]): [description]
            connection ([type]): [description]
        """
        return query

    @classmethod
    def applyEqualFilter(cls, query, field, value, model=None, allowEmptyStr=False):
        """
        精确匹配过滤
        :return:
        """
        if isinstance(value, str) and not value and not allowEmptyStr:  # 忽略空字符串匹配条件
            return query
        if model:
            modelField = getattr(model, field)
            query = query.filter(modelField == value)
        else:
            query = query.filter_by(**{field: value})
        return query

    @classmethod
    def applyLikeFilter(cls, query, field, value, model, leftLike=True, rightLike=True):
        """应用模糊匹配过滤

        Args:
            query ([type]): 原始query
            field ([type]): 过滤字段
            value ([type]): 字段内容
            model ([type]): [description]
            leftLike (bool, optional): 左侧是否模糊匹配, 将自动给value左侧加上%. Defaults to True.
            rightLike (bool, optional): 右侧是否模糊匹配, 将自动给value右侧加上%. Defaults to True.
        """
        if model:
            modelField = getattr(model, field)
            expr = value
            if leftLike and not expr.startswith('%'):
                expr = '%' + expr
            if rightLike and not expr.endswith('%'):
                expr = expr + '%'
            query = query.filter(modelField.like(expr))
            return query
        else:
            raise ValueError('like query must be used with model')

    @classmethod
    def applyDateRangeFilter(cls, query, field, start, end, model):
        """应用时间范围过滤

        Args:
            query ([type]): 原始query
            field ([type]): 过滤字段
            start ([type]): 开始时间, 不指定则无开始时间过滤, datetime格式或arrow可以识别的字符串格式
            end ([type]): 结束时间,不指定则无结束时间过滤, datetime格式或arrow可以识别的字符串格式
            model ([type], optional): [description]. Defaults to None.
        """
        if not start and not end:
            return query
        if model:
            modelField = getattr(model, field)
            if start:
                start = arrow.get(start).naive
                query = query.filter(modelField >= start)
            if end:
                end = arrow.get(end).naive
                query = query.filter(modelField <= end)
        else:
            raise ValueError('datetime filter must be used with model')

        return query
    
    def apply(self, query, connection, isSort=1):
        """将查询条件应用到query上
        """
        self.validate()
        query = self.applyFilter(query, connection)
        if isSort:
            query = self.applySort(query, connection)
        if not self.is_export:
            # 导出时不做翻页
            query = self.applyPageSize(query, connection)
        return query
    

