#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-08-03 23:07:43

'''
from brainmapanalyzer.dataset import DataSet
from brainmapanalyzer.extractor.rowselector import RowSelector
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import datetime

class FieldSourceInfo:
    """提取结果的来源信息
    """

    def __init__(self, table='', field='', id='', pos=()):
        """

        Args:
            table (str, optional): 来源表名. Defaults to ''.
            field (str, optional): 来源字段名. Defaults to ''.
            id (str, optional): 来源行的主键信息, 如果有多个需要拼一起. Defaults to ''.
            pos (tuple, optional): 字符串字段的起始和结束offset, 可能有多个, 这个字段是一个tuple的tuple Defaults to ().
            例如: 原始词为 "王中王", 要提取的内容是'王', 那么pos就可能是   ((0, 1), (2,3))
        """
        self.table = table
        self.field = field
        self.id = id
        self.pos = pos


class IndicatorConfigBase:
    """一个指标的配置"""
    
    def __init__(self, key: str, name: str):
        self.key = key
        if isinstance(key, bytes):
            self.key = key.decode('utf-8')
        self.name = name


class FieldResult:
    """一个指标的提取结果
    """
    def __init__(self, value, source: List[FieldSourceInfo]=[], field_type='str'):
        self.value = value
        self.source = source or []
        self.field_type = field_type
    
    def addSource(self, source):
        if isinstance(source, (tuple, list)):
            self.source.extend(source)
        else:
            self.source.append(source)


class BaseFieldExtractor:
    
    # 字段类型
    FIELD_TYPE_STRING = 'str'
    FIELD_TYPE_INT = 'integer'
    FIELD_TYPE_FLOAT = 'float'
    FIELD_TYPE_DATETIME = 'datetime'
    FIELD_TYPE_BOOL = 'boolean'
    FIELD_TYPE_LIST = 'list'
    # 记录类型, 与list实际一样, 相当于List[dict]
    FIELD_TYPE_RECORD = 'record'
    FIELD_TYPE_DICT = 'dict'
    
    def __init__(self, case: DataSet, ext_fields: Dict[str, Any]):
        self.case = case
        # 当前已经提取过的其他字段
        self.ext_fields = ext_fields
    
    @classmethod
    def getFieldType(cls, field_type):
        return {
            cls.FIELD_TYPE_BOOL: bool,
            cls.FIELD_TYPE_DATETIME: datetime.datetime,
            cls.FIELD_TYPE_FLOAT: float,
            cls.FIELD_TYPE_INT: int,
            cls.FIELD_TYPE_STRING: str,
            cls.FIELD_TYPE_LIST: list,
            cls.FIELD_TYPE_RECORD: list,
            cls.FIELD_TYPE_DICT: dict
        }.get(field_type, str)
    
    def extract(self, target_time=None, start_hours=7*24, end_hours=7*24) -> FieldResult:
        """提取字段并返回

        Args:
            target_time ([type], optional): 参照时间, 如果提供将选择距此时间最近的一条记录的值. Defaults to None.
            start_hours ([type], optional): 若target_time不为空则只保留晚于target_time前start_hours个小时的数据. Defaults to 7*24.
            end_hours ([type], optional): 若target_time不为空, 则只保留早于target_time之后end_hours小时之内的数据. Defaults to 7*24.
        """
        raise NotImplementedError()
    
class FieldExtractor(BaseFieldExtractor):
    
    def __init__(self, case: DataSet, ext_fields: Dict[str, Any], selector: RowSelector):
        super().__init__(case, ext_fields=ext_fields)
        self.selector = selector
    
    def setTimeField(self, field):
        """设置表中的时间字段
        """
        if field:
            self.selector.time_field = field
        return self
    
    def setSelectorTimeRange(self, target_time=None, start_hours=7*24, end_hours=7*24):
        """设置提取数据的时间范围
        """
        # 找到距离目标时间最近的一次                                                                                              
        if target_time:
            self.selector.after(target_time - datetime.timedelta(hours=start_hours))
            self.selector.before(target_time + datetime.timedelta(hours=end_hours))
            self.selector.near(target_time)
        return self
    
    @classmethod
    def extractIndicator(cls, indicators: List[IndicatorConfigBase], dataset: DataSet, 
                         target_time=None, start_hours=7*24, end_hours=7*24,
                         unique_tables: Iterable[str] = (),
                         time_fields: dict = None) -> Dict[str, FieldResult]:
        """从一组数据中提取指标

        Args:
            indicators (List[IndicatorConfig]): 所有指标的配置
            dataset (DataSet): 目标数据集
            target_time (datetime, optional): 目标时间, 提取的指标需要在目标时间前start_hours小时至目标时间后end_hours天之间且选择距离target_time最近的一次. Defaults to None.
            start_hours (int, optional): . Defaults to 7*24.
            end_hours (int, optional): . Defaults to 7*24.
            unique_tables (Iterable[str], optional): [description]. Defaults to ().
            time_fields (dict): 指定每个表的时间字段
        """
        raise NotImplementedError()
    