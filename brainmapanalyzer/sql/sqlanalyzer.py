#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-02-16 12:09:02

'''
from keyword import kwlist
from typing import Union
from brainmapanalyzer.keywords.keywords import Keyword
import brainmapanalyzer.keywords.operators as opers
from iyoudoctor.hosp.search.data_pb2 import Query, CompareQuery, AndQuery, OrQuery, NotQuery
from google.protobuf.json_format import MessageToDict, ParseDict

class SQLQueryAnalyzerBase:
    """将脑图转换成一个sql的where条件, 目前只能支持所有Keyword都是对应同一个表
    """
    DIALECT_MYSQL = 'mysql'
    DIALECT_TEXTX = 'textx'
    
    def __init__(self, query: Union[Query, OrQuery, AndQuery, NotQuery, CompareQuery]):
        self.query = query
    
    def getSQL(self, dialect='mysql') -> str:
        raise NotImplementedError()
    
    def quoteCondition(self, sql):
        if sql.startswith('(') and sql.endswith(')'):
            return sql
        else:
            return '(%s)' % sql


class SQLQueryAnalyzer(SQLQueryAnalyzerBase):
    
    def __init__(self, query: Query):
        self.query = query
        self._and = None
        self._or = None
        self._not = None
        self._compare = None
        
        if self.query.HasField('and'): # type: ignore
            self._and = AndSQLQueryAnalyzer(getattr(self.query, 'and')) # type: ignore
        if self.query.HasField('or'): # type: ignore
            self._or = OrSQLQueryAnalyzer(getattr(self.query, 'or')) # type: ignore
        if self.query.HasField('not'): # type: ignore
            self._not = NotSQLQueryAnalyzer(getattr(self.query, 'not')) # type: ignore
        if self.query.HasField('compare'): # type: ignore
            self._compare = CompareSQLQueryAnalyzer(self.query.compare) # type: ignore
            
    @classmethod
    def fromJson(cls, js):
        """从json结构的数据构建
        """
        query = Query()
        ParseDict(js, query) # type: ignore
        return cls(query)
    
    def getSQL(self, dialect='mysql'):
        sqls = []
        if self._and:
            sqls.append(self._and.getSQL(dialect))
        if self._or:
            sqls.append(self._or.getSQL(dialect))
        if self._not:
            sqls.append(self._not.getSQL(dialect))
        if self._compare:
            sqls.append(self._compare.getSQL(dialect))
        return ' and '.join([
            self.quoteCondition(item) for item in sqls if item
        ])


class AndSQLQueryAnalyzer(SQLQueryAnalyzerBase):
    
    def __init__(self, query: AndQuery):
        super().__init__(query)
        self.children = []
        for q in self.query.values: # type: ignore
            self.children.append(SQLQueryAnalyzer(q))
    
    def getSQL(self, dialect='mysql') -> str:
        sqls = [child.getSQL(dialect) for child in self.children]
        return ' and '.join([
            self.quoteCondition(item) for item in sqls if item
        ])
    

class OrSQLQueryAnalyzer(SQLQueryAnalyzerBase):
    
    def __init__(self, query: AndQuery):
        super().__init__(query)
        self.children = []
        for q in self.query.values: # type: ignore
            self.children.append(SQLQueryAnalyzer(q))
    
    def getSQL(self, dialect='mysql') -> str:
        sqls = [child.getSQL(dialect) for child in self.children]
        return ' or '.join([
            self.quoteCondition(item) for item in sqls if item
        ])
    
    
class NotSQLQueryAnalyzer(SQLQueryAnalyzerBase):
    
    def __init__(self, query: NotQuery):
        super().__init__(query)
        self.child = SQLQueryAnalyzer(query.value) # type: ignore
    
    def getSQL(self, dialect='mysql') -> str:
        sql = self.child.getSQL(dialect)
        return 'not %s' % self.quoteCondition(sql)


class CompareSQLQueryAnalyzer(SQLQueryAnalyzerBase):
    """每一个CompareQuery及其children构成了一个RowSelector, RowSelector能获取到结果表示符合条件
    """
    
    def __init__(self, query: CompareQuery):
        super().__init__(query)
        # 关键词
        self.kword = self.getKeyWord()
        self.operator = self.query.operator
        
    @property
    def Values(self) -> list:
        return self.query.values # type: ignore
        
    def getKeyWord(self) -> Keyword:
        """获取keyword"""
        return Keyword(
            tablename=self.query.params["tablename"], # type: ignore
            field=self.query.params['field'], # type: ignore
            fieldtype=self.query.params['fieldtype'] # type: ignore
        )
        
    def wrap(self, s, dialect):
        """字符串加引号"""
        #if dialect == self.DIALECT_TEXTX:
        #    # CDSS规则引擎不转义
        #    return s
        if self.kword.fieldtype == self.kword.FIELD_TYPE_STRING or self.kword.fieldtype == self.kword.FIELD_TYPE_DATETIME:
            return "'%s'" % s
        else:
            return s
        
    def quote(self, s, dialect='mysql'):
        if dialect == self.DIALECT_MYSQL:
            return '`%s`'  % s
        else:
            return s
    
    def wrapList(self, l: list, dialect: str):
        """使用in操作符时将列表转换成右值

        Args:
            l (list): [description]
            dialect (str]): [description]

        Returns:
            [type]: [description]
        """
        if dialect == self.DIALECT_TEXTX:
            return "'[%s]'" % ','.join([str(item) for item in l])
        else:
            return '(%s)' % ','.join([self.wrap(item, dialect) for item in l])
    
    def getSQL(self, dialect='mysql') -> str:
        #op = self.operator._id
        op = self.operator
        val1, val2 = None, None
        if self.Values:
            if len(self.Values) >= 1:
                val1 = self.Values[0]
            elif len(self.Values) >= 2:
                val2 = self.Values[1]
        sqls = []
        if op == opers.OPT_EQ:
            if len(self.Values) == 1:
                sqls.append('%s = %s' % (self.quote(self.kword.field, dialect=dialect), self.wrap(val1, dialect)))
            else:
                sqls.append('%s in %s' % (self.quote(self.kword.field, dialect=dialect), self.wrapList(self.Values, dialect)))
        elif op == opers.OPT_BW:
            sqls.append('%s > %s and %s <= %s' % (self.quote(self.kword.field, dialect=dialect), self.wrap(val1, dialect), self.quote(self.kword.field, dialect=dialect), self.wrap(val2, dialect)))
        elif op == opers.OPT_GT:
            sqls.append('%s > %s' % (self.quote(self.kword.field, dialect=dialect), val1))
        elif op == opers.OPT_GTE:
            sqls.append('%s >= %s' % (self.quote(self.kword.field, dialect=dialect), val1))
        elif op == opers.OPT_LT:
            sqls.append('%s < %s' % (self.quote(self.kword.field, dialect=dialect), val1))
        elif op == opers.OPT_LTE:
            sqls.append('%s <= %s' % (self.quote(self.kword.field, dialect=dialect), val1))
        elif op == opers.OPT_INCLUDE:
            tmp = []
            # 包含任何一个就算包含
            if dialect == self.DIALECT_TEXTX:
                for val in self.Values:
                    tmp.append("%s like '%%%s%%'" % (self.quote(self.kword.field, dialect=dialect), val))
            else:
                for val in self.Values:
                    tmp.append('"%s" in %s' % (val, self.quote(self.kword.field, dialect=dialect)))
            sqls.append(' or '.join([self.quoteCondition(item) for item in tmp]))
        elif op == opers.OPT_EXCLUDE:
            tmp = []
            # 所有都不包含才是不包含
            if dialect == self.DIALECT_TEXTX:
                for val in self.Values:
                    tmp.append('not ("%s" in %s)' % (val, self.quote(self.kword.field, dialect=dialect)))
            else:
                for val in self.Values:
                    tmp.append("%s not like '%%%s%%'" % (self.quote(self.kword.field, dialect=dialect), val))
            sqls.append(' and '.join([self.quoteCondition(item) for item in tmp]))
        elif op == opers.OPT_REGEX:
            sqls.append("%s REGEXP '%s'" % (self.quote(self.kword.field, dialect=dialect), val1))
        elif op == opers.OPT_IS:
            sqls.append("%s = 1" % self.quote(self.kword.field, dialect=dialect))
        elif op == opers.OPT_ISNOT:
            sqls.append("%s = 0" % self.quote(self.kword.field, dialect=dialect))
        elif op == opers.OPT_NE:
            if len(self.Values) == 1:
                sqls.append('%s != %s' % (self.quote(self.kword.field), self.wrap(val1, dialect)))
            else:
                sqls.append('%s not in %s' % (self.quote(self.kword.field, dialect=dialect), self.wrapList(self.Values, dialect)))
        else:
            raise ValueError('unknown operator %s' % op)
        # 关联属性
        if self.query.children: # type: ignore
            for child in self.query.children: # type: ignore
                q = CompareSQLQueryAnalyzer(child)
                sqls.append(q.getSQL(dialect))
        return ' and '.join([self.quoteCondition(item) for item in sqls])
