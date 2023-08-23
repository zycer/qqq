#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-03-22 18:16:28

'''
from typing import Any, Dict, Iterable, List, Optional, Union
from brainmapanalyzer.dataset import DataSet
from brainmapanalyzer.extractor.fieldextractor import FieldExtractor, FieldResult, IndicatorConfigBase
from brainmapanalyzer.extractor.fieldselector import FieldSelector
from brainmapanalyzer.logic.logicanalyzer import AndLogicQueryAnalyzer, CompareLogicQueryAnalyzer, LogicQueryAnalyzer, LogicQueryAnalyzerBase, NotLogicQueryAnalyzer, OrLogicQueryAnalyzer
from brainmapanalyzer.extractor.rowselector import RowSelector
import json
import logging


class BrainmapIndicatorConfig(IndicatorConfigBase):
    """基于脑图来提取指标的指标配置
    """
    # 聚合类型
    AGG_TYPE_MAX = 'max' # 选最大的, 必须是数值型或时间
    AGG_TYPE_MIN = 'min' # 选最小的, 必须是数值型或时间
    AGG_TYPE_FIRST = 'first' # 选时间排序后的第一个, 必须提供time_field
    AGG_TYPE_LAST = 'last'  # 选时间排序最后一个, 必须提供time_field
    AGG_TYPE_AVG = 'avg'  # 求平均值, 必须是数值型
    AGG_TYPE_SUM = 'sum'  # 求和, 必须是数值型
    AGG_TYPE_COUNT = 'count' # 计数
    AGG_TYPE_ALL = 'all'  # 全都要, 结果只能返回字符串, 多条用换行分割
    
    def __init__(self, key: str, name: str, 
                 include_query: Union[dict, str]='', exclude_query: Union[dict, str]='', 
                 field_path: str='', field_type=FieldExtractor.FIELD_TYPE_STRING,
                 index=None,
                 agg_type='all'
                 ):
        super().__init__(key, name)
        # 脑图纳排条件
        include_query = include_query or {}
        exclude_query = exclude_query or {}
        self.include_query = json.loads(include_query) if isinstance(include_query, str) else include_query
        self.exclude_query = json.loads(exclude_query) if isinstance(exclude_query, str) else exclude_query
        # 要提取的字段名称, 如果不指定则强制为布尔型, 只要符合条件就是true
        self.field_path = field_path
        # 字段类型
        self.field_type = field_type
        # 聚合类型
        self.agg_type = agg_type
        # 求平均数必须先返回list
        if self.agg_type in (self.AGG_TYPE_AVG, self.AGG_TYPE_SUM, self.AGG_TYPE_COUNT, self.AGG_TYPE_MAX, self.AGG_TYPE_MIN):
            self.field_type = FieldExtractor.FIELD_TYPE_LIST
        # 要所有结果, 类型只能是string
        elif self.agg_type == self.AGG_TYPE_ALL:
            self.field_type = FieldExtractor.FIELD_TYPE_STRING
        # 要取符合条件的第几条
        self.index = index
            
    def apply(self, selector: RowSelector):
        if self.agg_type == self.AGG_TYPE_FIRST:
            selector.setIndex(0)
        elif self.agg_type == self.AGG_TYPE_LAST:
            selector.setIndex(-1)
        else:
            selector.setIndex(self.index)
            
        
    def getAnalyzer(self) -> LogicQueryAnalyzer:
        """根据纳排条件获取对应的LogicQueryAnalyzer
        """
        if not self.include_query and not self.exclude_query:
            raise ValueError('at least one query need to be specified')
        if not self.include_query:
            query = self.exclude_query
        elif not self.exclude_query:
            query = self.include_query
        else:
            # 纳入排除条件都存在
            query = {
                'and': {'values': [self.include_query]},
                'not': {'value': self.exclude_query}
            }
        return LogicQueryAnalyzer.fromJson(query)
    
    def postProcess(self, val):
        """对提取出来的结果做后处理
        """
        if val is None:
            return None
        if self.agg_type == self.AGG_TYPE_SUM:
            return sum(val)
        elif self.agg_type == self.AGG_TYPE_COUNT:
            return len(val)
        elif self.agg_type == self.AGG_TYPE_AVG:
            if len(val) == 0:
                return 0
            return sum(val) / len(val)
        elif self.agg_type == self.AGG_TYPE_MAX:
            return max(val)
        elif self.agg_type == self.AGG_TYPE_MIN:
            return min(val)
        return val     


class BrainmapFieldExtractor(FieldExtractor):
    """基于脑图配置提取字段
    """
    
    def __init__(self, case: DataSet, result: Dict[str, Any], analyzer: LogicQueryAnalyzer, 
                 field_path: str, field_type="str"):
        """

        Args:
            case (DataSet): 完整病历的数据集
            result (Dict[str, Any]): 已经提取出来的所有字段, 某些全局字段也可以放在这里面
            analyzer (LogicQueryAnalyzer): 脑图解析出来的结构, 只能支持单个表的query, 跨表则只能判断有无. 如果指定的是CompareLogicQueryAnalyzer则tablename已由kword确定, 否则需要指定tablename参数
            field_path (str): 要提取的字段名称
            field_type (str, optional): 目标字段类型. Defaults to "str".
        """
        self.analyzer = analyzer
        self.field_path = field_path
        selector = RowSelector.getRowSelector(self.getTableName(analyzer)).filter(analyzer.getRowFilter()) # type: ignore
        super().__init__(case, result, selector)
        self.fieldSelector = FieldSelector(self.selector, field_path, field_type=self.getFieldType(field_type))
        
    def getTableName(self, analyzer: Optional[LogicQueryAnalyzerBase]):
        """提取出tablename, 找到任何一个CompareLogicQueryAnalyzer获取他的tablename, 不考虑关键字来自不同表的情况, 调用方需要保证所有关键字都来自同一个表
        """
        if not analyzer:
            return ''
        if isinstance(analyzer, CompareLogicQueryAnalyzer):
            return analyzer.kword.tablename
        elif isinstance(analyzer, LogicQueryAnalyzer):
            return self.getTableName(analyzer._compare) or self.getTableName(analyzer._and) or self.getTableName(analyzer._or) or self.getTableName(analyzer._not)
        elif isinstance(analyzer, (AndLogicQueryAnalyzer, OrLogicQueryAnalyzer)):
            for child in analyzer.children:
                tablename = self.getTableName(child)
                if tablename:
                    return tablename
        elif isinstance(analyzer, NotLogicQueryAnalyzer):
            return self.getTableName(analyzer.child)
        return ''
        
    def extract(self, target_time=None, start_hours=7 * 24, end_hours=7 * 24) -> FieldResult:
        """提取字段并返回

        Args:
            target_time (datetime, optional): 参照时间, 如果提供将选择距此时间最近的一条记录的值. Defaults to None.
            start_hours (int, optional): 若target_time不为空则只保留晚于target_time前start_hours个小时的数据. Defaults to 7*24.
            end_hours (int, optional): 若target_time不为空, 则只保留早于target_time之后end_hours小时之内的数据. Defaults to 7*24.
        """
        # 设置必须提取target_time最近的一次且在前start_hours小时到后end_hours小时之间
        self.setSelectorTimeRange(target_time=target_time, start_hours=start_hours, end_hours=end_hours)
        
        return self.fieldSelector.getSuggestion(self.case, self.ext_fields)
        
    @classmethod
    def extractIndicator(cls, indicators: List[BrainmapIndicatorConfig], dataset: DataSet, 
                         target_time=None, start_hours=7*24, end_hours=7*24,
                         unique_tables: Iterable[str] = (),
                         time_fields: dict = None) -> Dict[str, FieldResult]:
        """从一组数据中提取指标

        Args:
            indicators (List[IndicatorConfig]): 所有指标的配置, 字段之间有依赖关系时要保证先后顺序, 否则依赖字段无法提取出来.
            dataset (DataSet): 目标数据集
            target_time (datetime, optional): 目标时间, 提取的指标需要在目标时间前start_hours小时至目标时间后end_hours天之间且选择距离target_time最近的一次. Defaults to None.
            start_hours (int, optional): . Defaults to 7*24.
            end_hours (int, optional): . Defaults to 7*24.
            unique_tables (Iterable[str], optional): [description]. Defaults to ().
            time_fields (dict): 指定每个表的时间字段
        """
        time_fields = time_fields or {}
        # 可以在提取过程中被引用的字段
        ext_fields = {}
        # 本次提取出来的字段
        result = {}
        # 同一个dataset中唯一的表可以当做已经提取好的字段来使用, 这里不做校验, 调用方需要保证dataset中不存在重复记录
        for tablename in unique_tables:
            for _, row in dataset.iterrows(tablename):
                ext_fields.update({f"{tablename}|{k}": v for k, v in row.items()})
                break
        for indicator in indicators:
            extractor = BrainmapFieldExtractor(dataset, ext_fields, indicator.getAnalyzer(), indicator.field_path, indicator.field_type)
            extractor.setTimeField(time_fields.get(extractor.selector.tablename))
            indicator.apply(extractor.selector)
            val = extractor.extract(target_time=target_time, start_hours=start_hours, end_hours=end_hours)
            if val is not None:
                # 计算聚合结果
                tmp = indicator.postProcess(val.value)
                val.value = tmp
                result[indicator.key] = val
                ext_fields[indicator.key] = val.value
                logging.info('%s: %s', indicator.key, val)
        return result
        