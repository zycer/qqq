#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
from ast import Dict
from typing import Any, Iterable, List, Optional, Tuple
from brainmapanalyzer.dataset import DataSet
from dateutil.parser import parse
from .rowfilter import RowFilter
from baselib.utils import attrdict
from datetime import datetime
import logging


class RowSelector(object):

    def __init__(self, tablename, time_field=None, before=None, after=None, 
                 index=None, near_time: Optional[datetime]=None,
                 max_field_name=None, max_field_type=None,
                 min_field_name=None, min_field_type=None, 
                 time_ranges=None):
        # 表名
        self.tablename = tablename
        # 实体中用于表示时间的字段
        self.time_field = time_field
        # 获取此时间之前的数据
        self._before = before
        # 获取此时间之后的数据
        self._after = after
        # 获取满足条件的第几次数据, None表示所有, 其他同数组下标, -1表示最后一次
        self._index = index
        # 表过滤器
        self._filter = None
        # 跨列关联, 当前过滤的行的visit_id必须在另一个select过滤出的visit_id集合中
        self._join_visit_selectors = []

        # 取某字段为最大值的记录
        self._max_field_name = max_field_name
        self._max_field_type = max_field_type

        # 取某字段为最小值的字段
        self._min_field_name = min_field_name
        self._min_field_type = min_field_type
        
        # 选择距离此时间最近的记录
        self._near_time: Optional[datetime] = near_time
        # 选择的记录需要介于给定的时间范围内
        self._time_ranges: List[Tuple[datetime, datetime]] = time_ranges or []
    
    def getID(self, row):
        """获取主键
        """
        return row.get('_key') or row.get('_id') or row.get('id')
    
    def near(self, near_time):
        """取距离此时间最近的记录, 优先级  max/min > near > index"""
        self._near_time = near_time

    def max(self, max_field_name, max_field_type=float):
        '''取某字段最大的记录
        
        Args:
            max_field_name ([type]): 字段名称
            max_field_type ([type], optional): Defaults to float. 字段类型
        '''

        self._max_field_name = max_field_name
        self._max_field_type = max_field_type
        return self
    
    def min(self, min_field_name, min_field_type=float):
        """取某字段最小的记录
        
        Args:
            min_field_name ([type]): 字段名称
            min_field_type ([type], optional): Defaults to float. 字段类型
        """

        self._min_field_name = min_field_name
        self._min_field_type = min_field_type
        return self
    
    def setIndex(self, index):
        """设置要过滤符合条件的第几条记录
        """
        self._index = index
        return self
    
    def addTimeRange(self, start_time: datetime, end_time: datetime):
        """设置行需要符合的时间条件
        """
        self._time_ranges.append((start_time, end_time))

    def filter(self, f):
        '''过滤不满足条件的结果
        Args:
            f (TableFilter): 
        '''

        if self._filter is not None:
            self._filter = self._filter & f
        else:
            self._filter = f
        return self
    

    @classmethod
    def getRowSelector(cls, tablename, before=None, after=None, index=None):
        # 已废弃, 用于支持来自于hbase的数据
        selector = {
            'info:visit': VisitRowSelector(before, after, index),
            'info:operation': OperationRowSelector(before, after, index),
            'info:diagnosis': DiagnosisRowSelector(before, after, index),
            'emr:data': EmrRowSelector(before, after, index),
            'order:data': OrderRowSelector(before, after, index),
            'exam:data': ExamRowSelector(before, after, index),
            'lab:report': LabRowSelector(before, after, index),
            'exam:vital': VitalRowSelector(before, after, index),
            'info:eventpoint': EventRowSelector(before, after, index),
        }.get(tablename)
        if not selector:
            return cls(tablename, before=before, after=after, index=index)
        else:
            return selector

    def getTime(self, row) -> Optional[datetime]:
        """获取时间字段
        """
        time_val = row.get(self.time_field)
        if not time_val:
            return None
        if isinstance(time_val, datetime):
            return time_val
        return parse(time_val).replace(tzinfo=None)
    
    def checkTime(self, row):
        """检查行的时间是否符合条件
        """
        row_time = self.getTime(row)
        if not row_time:
            # 没有设置时间条件则直接通过
            if self._before is not None or self._after is not None or self._time_ranges:
                return False
            else:
                return True
        if isinstance(row_time, datetime):
            if self._before is not None and row_time > self._before:
                return False
            if self._after is not None and row_time < self._after:
                return False
            # 任何一个时间范围满足则满足条件
            if self._time_ranges:
                for start_time, end_time in self._time_ranges:
                    if start_time < row_time and row_time < end_time:
                        return True
                return False
        return True

    def iterrows(self, dataset: DataSet, ext_fields: dict =None) -> Iterable[Any]:
        """迭代遍历符合当前配置条件的行

        Args:
            dataset (DataSet): [description]
            ext_fields (dict): 已经提取到的其他字段
        """
        ext_fields = ext_fields or {}
        logging.debug('rowselector.iterrows: %s', ext_fields)
        if self.tablename == 'lab:report' or self.tablename == 'info:operation':
            for _, row in dataset.iterrows(tablename=self.tablename):
                row_time = self.getTime(row)
                if not row_time:
                    continue
                if self._before is not None and row_time > self._before:
                    continue
                if self._after is not None and row_time < self._after:
                    continue
                for detail in row.detail:
                    tmp = dict(detail.obj)
                    for k, v in row.items():
                        if k != 'detail':
                            tmp[k] = v
                    child = attrdict(tmp)
                    if self._filter and not self._filter.check(child, ext_fields):
                        continue
                    yield child
        elif self.tablename == 'emr:data':
            for _, row in dataset.iterrows(tablename=self.tablename):
                row_time = self.getTime(row)
                if not row_time:
                    continue
                if self._before is not None and row_time > self._before:
                    continue
                if self._after is not None and row_time < self._after:
                    continue
                for detail in row.content:
                    tmp = dict(detail.obj)
                    for k, v in row.items():
                        if k != 'content':
                            tmp[k] = v
                    child = attrdict(tmp)
                    if self._filter and not self._filter.check(child, ext_fields):
                        continue
                    yield child
        else:
            for _, row in dataset.iterrows(tablename=self.tablename):
                if not self.checkTime(row):
                    continue
                if self._filter and not self._filter.check(row, ext_fields):
                    continue
                yield row
                
    def exists(self, dataset) -> bool:
        """检查是否有符合条件的数据
        """
        for row in self.iterrows(dataset):
            return True
        return False

    def select(self, dataset, ext_fields: dict = None) -> list:
        '''返回此实体对应的数据
        '''
        ext_fields = ext_fields or {}
        result = []

        for row in self.iterrows(dataset, ext_fields):
            result.append(row)

        # 取最大或最小的记录
        if result:
            if self._max_field_name:
                if self._max_field_type is int:
                    result.sort(key=lambda row: int(row.get(self._max_field_name)) if row.get(self._max_field_name) else -999999999)
                elif self._max_field_type is float:
                    result.sort(key=lambda row: float(row.get(self._max_field_name)) if row.get(self._max_field_name) else 0)
                else:
                    # 日期字段也可以直接比较字符串
                    result.sort(key=lambda row: row.get(self._max_field_name))
                result = [result[-1]]
            elif self._min_field_name:
                if self._min_field_type is int:
                    result.sort(key=lambda row: int(row.get(self._min_field_name)))
                elif self._min_field_type is float:
                    result.sort(key=lambda row: float(row.get(self._min_field_name)))
                else:
                    # 日期字段可以直接比较字符串
                    result.sort(key=lambda row: row.get(self._min_field_name))
                result = [result[0]]
        
        # 排序
        if self.time_field:
            # 过滤掉没有时间字段的数据
            count_before = len(result)
            result = [row for row in result if row.get(self.time_field)]
            if len(result) < count_before:
                logging.warning('[%s]filter rows without time_field, before: %s, after: %s', self.tablename, count_before, len(result))
            result.sort(key=lambda row: row.get(self.time_field))
        if not result:
            return result
        # 找到距离_near_time最近的一条记录
        if self.time_field and self._near_time:
            delta = None
            final = None
            for item in result:
                t = self.getTime(item)
                if not t:
                    continue
                ts = (t - self._near_time).total_seconds()
                if ts < 0:
                    ts = 0 - ts
                if delta is None or delta > ts:
                    delta = ts
                    final = item
            return [final]
        
        elif self._index is not None:
            try:
                result = [result[self._index]]
            except IndexError:
                result = []
        return result
    
    def last(self):
        '''只取最后一次数据
        '''
        self._index = -1
        return self

    def all(self):
        '''取所有数据
        '''
        self._index = None
        return self

    def first(self):
        '''只取第一次数据
        '''
        self._index = 0
        return self

    def before(self, dt):
        """取此时间之前的数据

        Args:
            dt (datetime): 
        """
        self._before = dt
        return self

    def after(self, dt):
        '''取此时间之后的数据

        Args:
            dt (datetime): 
        '''
        self._after = dt
        return self


class LabRowSelector(RowSelector):
    '''化验表'''

    def __init__(self, before=None, after=None, index=None):
        super(LabRowSelector, self).__init__(
            'lab:report', 'time', before, after, index)
    
    def getID(self, row):
        return row.get('id') + '_' + row.get('rawid')


class DiagnosisRowSelector(RowSelector):
    '''诊断表'''

    def __init__(self, before=None, after=None, index=None):
        super(DiagnosisRowSelector, self).__init__(
            'info:diagnosis', 'date', before, after, index)
    
    def getID(self, row):
        return row.get('id')


class OrderRowSelector(RowSelector):
    '''医嘱表'''

    def __init__(self, before=None, after=None, index=None):
        super(OrderRowSelector, self).__init__('order:data',
                                               'enter_date_time', before, after, index)
    
    def getID(self, row):
        return row.get('no')

class EmrRowSelector(RowSelector):

    def __init__(self, before=None, after=None, index=None):
        super(EmrRowSelector, self).__init__(
            'emr:data', 'time', before, after, index)
        
    def getID(self, row):
        return row.get('id') + '_' + row.get('rawid')
    

class VisitRowSelector(RowSelector):

    def __init__(self, before=None, after=None, index=None):
        super(VisitRowSelector, self).__init__('info:visit',
                                               'admission_date_time', before, after, index)
        
    def getID(self, row):
        return row.get('visit_id')
    

class ExamRowSelector(RowSelector):

    def __init__(self, before=None, after=None, index=None):
        super(ExamRowSelector, self).__init__(
            'exam:data', 'time', before, after, index)
    

class VitalRowSelector(RowSelector):

    def __init__(self, before=None, after=None, index=None):
        super(VitalRowSelector, self).__init__(
            'exam:vital', 'time', before, after, index)
    

class OperationRowSelector(RowSelector):

    def __init__(self, before=None, after=None, index=None):
        super(OperationRowSelector, self).__init__(
            'info:operation', 'time', before, after, index)
        
    def getID(self, row):
        return row.get('id') + '_' + row.get('rawid')    


class EventRowSelector(RowSelector):

    def __init__(self, before=None, after=None, index=None):
        super(EventRowSelector, self).__init__(
            'info:eventpoint', 'time', before, after, index)

