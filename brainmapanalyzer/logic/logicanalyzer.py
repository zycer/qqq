#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-02-16 09:43:25

'''

from typing import List, Union
from brainmapanalyzer.keywords.keywords import Keyword
from brainmapanalyzer.dataset import DataSet
from iyoudoctor.hosp.search.data_pb2 import Query, CompareQuery, AndQuery, OrQuery, NotQuery
from brainmapanalyzer.extractor.rowfilter import RowFieldFilter, RowFilter
from brainmapanalyzer.extractor.rowselector import RowSelector
import brainmapanalyzer.keywords.operators as opers
import logging
from google.protobuf.json_format import MessageToDict, ParseDict
import arrow
import datetime

class LogicQueryAnalyzerBase:
    """将脑图转换成逻辑表达式, 可以判断一个输入数据集是否符合当前脑图条件
    """
    
    def __init__(self, query: Union[Query, OrQuery, AndQuery, NotQuery, CompareQuery]):
        self.query = query
        
    def check(self, dataset: DataSet):
        raise NotImplementedError()
    
    def getRowFilter(self) -> RowFilter:
        raise NotImplementedError()
    

class LogicQueryAnalyzer(LogicQueryAnalyzerBase):
    
    def __init__(self, query: Query):
        self.query = query
        # 对应Query中的子query, 暂不支持text和control
        self._and = None
        self._or = None
        self._not = None
        self._compare = None
        
        if self.query.HasField("and"): # type: ignore
            self._and = AndLogicQueryAnalyzer(getattr(self.query, "and")) # type: ignore
        if self.query.HasField("or"):  # type: ignore
            self._or = OrLogicQueryAnalyzer(getattr(self.query, "or")) # type: ignore
        if self.query.HasField("not"): # type: ignore
            self._not = NotLogicQueryAnalyzer(getattr(self.query, "not")) # type: ignore
        if self.query.HasField('compare'): # type: ignore
            self._compare = CompareLogicQueryAnalyzer(self.query.compare) # type: ignore
            
    @classmethod
    def fromJson(cls, js):
        """从json结构的数据构建
        """
        query = Query()
        ParseDict(js, query) # type: ignore
        return cls(query)
    
    def check(self, dataset: DataSet):
        """所有的子query都返回真才为真, 目前忽略text和control
        """
        if self._and and not self._and.check(dataset):
            return False
        if self._or and not self._or.check(dataset):
            return False
        if self._not and not self._not.check(dataset):
            return False
        if self._compare and not self._compare.check(dataset):
            return False
        return True
    
    def getRowFilter(self) -> RowFilter:
        """获取RowFilter, 目前仅支持全部字段来自同一个张表
        """
        ft: RowFilter = None # type: ignore
        for item in [self._and, self._or, self._not, self._compare]:
            if not item:
                continue
            if not ft:
                ft = item.getRowFilter()
            else:
                ft = ft & item.getRowFilter()
        return ft

class AndLogicQueryAnalyzer(LogicQueryAnalyzerBase):
    
    def __init__(self, query: AndQuery):
        super().__init__(query)
        self.children = []
        for q in self.query.values: # type: ignore
            self.children.append(LogicQueryAnalyzer(q))
    
    def check(self, dataset: DataSet):
        """任何一个child为假则返回假"""
        for child in self.children:
            if not child.check(dataset):
                return False
        return True
    
    def getRowFilter(self) -> RowFilter:
        ft: RowFilter = None # type: ignore
        for item in self.children:
            if not item:
                continue
            if not ft:
                ft = item.getRowFilter()
            else:
                ft = ft & item.getRowFilter()
        return ft


class OrLogicQueryAnalyzer(LogicQueryAnalyzerBase):
    
    def __init__(self, query: AndQuery):
        super().__init__(query)
        self.children = []
        for q in self.query.values: # type: ignore
            self.children.append(LogicQueryAnalyzer(q))
    
    def check(self, dataset: DataSet):
        """任何一个child为真则立刻返回真"""
        for child in self.children:
            if child.check(dataset):
                return True
        return False
    
    def getRowFilter(self) -> RowFilter:
        ft: RowFilter = None # type: ignore
        for item in self.children:
            if not item:
                continue
            if not ft:
                ft = item.getRowFilter()
            else:
                ft = ft | item.getRowFilter()
        return ft
    
class NotLogicQueryAnalyzer(LogicQueryAnalyzerBase):
    
    def __init__(self, query: NotQuery):
        super().__init__(query)
        self.child = LogicQueryAnalyzer(query.value) # type: ignore
    
    def check(self, dataset: DataSet):
        return not self.child.check(dataset)
    
    def getRowFilter(self) -> RowFilter:
        return ~self.child.getRowFilter()


class CompareLogicQueryAnalyzer(LogicQueryAnalyzerBase):
    """每一个CompareQuery及其children构成了一个RowSelector, RowSelector能获取到结果表示符合条件
    """
    
    def __init__(self, query: CompareQuery):
        super().__init__(query)
        # 关键词
        self.kword = self.getKeyWord()
        self.operator = self.query.operator # type: ignore
        #self.operator = self.kword.getOperator(self.query.operator) # type: ignore
        self.rowFilter = self.analyze()
        
    @property
    def Values(self) -> list:
        return self.query.values # type: ignore
    
    def getRowSelector(self) -> RowSelector:
        # 转换成RowSelector
        return RowSelector(tablename=self.kword.tablename).filter(self.rowFilter)
        
    def getKeyWord(self) -> Keyword:
        """获取keyword"""
        return Keyword(
            tablename=self.query.params["tablename"], # type: ignore
            field=self.query.params['field'], # type: ignore
            fieldtype=self.query.params['fieldtype'] # type: ignore
        )
        
    def convertValue(self, val: str):
        """将右值转换成与当前字段类型一致的变量

        Args:
            val (str): 输入的操作数
        """
        # 变量不做转换
        if val.startswith('${') and val.endswith('}'):
            return val
        if self.kword.fieldtype == self.kword.FIELD_TYPE_DATETIME:
            return datetime.datetime.strptime(val, '%Y-%m-%d')     
        elif self.kword.fieldtype == self.kword.FIELD_TYPE_INT:
            return int(val)
        elif self.kword.fieldtype == self.kword.FIELD_TYPE_FLOAT:
            return float(val)
        else:
            return val
    
    def analyze(self) -> RowFilter:
        f: RowFilter = None # type: ignore
        op = self.operator
        val1, val2 = '', ''
        if self.query.values: # type: ignore
            if len(self.Values) >= 1:
                val1 = self.Values[0]
            if len(self.Values) >= 2:
                val2 = self.Values[1]
        if op == opers.OPT_EQ:
            f = RowFieldFilter(self.kword.field, is_in=[self.convertValue(item) for item in self.Values])
        elif op == opers.OPT_BW:
            f = RowFieldFilter(self.kword.field, gt_value=self.convertValue(val1), lte_value=self.convertValue(val2))
        elif op == opers.OPT_GT:
            f = RowFieldFilter(self.kword.field, gt_value=self.convertValue(val1))
        elif op == opers.OPT_GTE:
            f = RowFieldFilter(self.kword.field, gte_value=self.convertValue(val1))
        elif op == opers.OPT_LT:
            f = RowFieldFilter(self.kword.field, lt_value=self.convertValue(val1))
        elif op == opers.OPT_LTE:
            f = RowFieldFilter(self.kword.field, lte_value=self.convertValue(val1))
        elif op == opers.OPT_INCLUDE:
            # 包含任何一个就算包含
            if self.kword.fieldtype == Keyword.FIELD_TYPE_LIST:
                # 数组的包含实际上是元素的等于, 直接使用is_in是因为RowFieldFilter会将数组展开对每个元素进行check
                f = RowFieldFilter(self.kword.field, is_in=self.Values)
            else:
                # 字符串的包含是真的字符串包含
                for val in self.Values:
                    if not f:
                        f = RowFieldFilter(self.kword.field, contain_value=self.convertValue(val))
                    else:
                        f = f | RowFieldFilter(self.kword.field, contain_value=self.convertValue(val))
        elif op == opers.OPT_EXCLUDE:
            # 所有都不包含才是不包含, 对于数组是所有的元素都不等于才是不等于
            if self.kword.fieldtype == Keyword.FIELD_TYPE_LIST:
                f = ~RowFieldFilter(self.kword.field, is_in=self.Values)
            else:
                for val in self.Values:
                    if not f:
                        f = ~RowFieldFilter(self.kword.field, contain_value=self.convertValue(val))
                    else:
                        f = f & (~RowFieldFilter(self.kword.field, contain_value=self.convertValue(val)))
        elif op == opers.OPT_REGEX:
            f = RowFieldFilter(self.kword.field, regex=val1)
        elif op == opers.OPT_IS:
            f = RowFieldFilter(self.kword.field, equal_value=True)
        elif op == opers.OPT_ISNOT:
            f = RowFieldFilter(self.kword.field, equal_value=False)
        elif op == opers.OPT_NE:
            f = ~RowFieldFilter(self.kword.field, is_in=[self.convertValue(item) for item in self.Values])
        elif op == opers.OPT_BW_FIELD:
            # 有3个操作数, 分别是 参照时间, 前多少天, 后多少天
            f = RowFieldFilter(self.kword.field).inTimeRange(ref=self.Values[0], start_days=self.Values[1], end_days=self.Values[2])
        else:
            raise ValueError('unknown operator %s' % op)
        # 关联属性
        if self.query.children: # type: ignore
            for child in self.query.children: # type: ignore
                q = CompareLogicQueryAnalyzer(child)
                f = f & q.rowFilter
        return f

    def select(self, dataset: DataSet) -> list:
        """获取符合条件的数据
        """
        rows = self.getRowSelector().select(dataset)
        return rows
    
    def check(self, dataset: DataSet):
        """检查输入数据是否符合当前条件
        """
        ret = self.getRowSelector().exists(dataset)
        return ret
    
    def getRowFilter(self) -> RowFilter:
        return self.rowFilter