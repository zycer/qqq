#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-03-22 14:23:27

'''
import json
from typing import Dict, Iterable, List, Optional
from brainmapanalyzer.dataset import DataSet
from brainmapanalyzer.extractor.fieldextractor import FieldExtractor, IndicatorConfigBase, FieldResult
from brainmapanalyzer.extractor.rowselector import RowSelector
from brainmapanalyzer.extractor.fieldselector import FieldSelector
from brainmapanalyzer.extractor.rowfilter import RowFilter, RowFieldFilter
import logging

class TimeFilterConfig:
    """时间过滤配置, 用于控制在另一个字段之前还是之后"""
    
    def __init__(self, field, start_days=0, end_days=0):
        self.field = field
        # 过滤参考字段前 start 天至后 end 天的数据
        self.start_days = start_days
        self.end_days = end_days
    
    def apply(self, selector: RowSelector):
        if selector.time_field:
            f = RowFieldFilter(selector.time_field).inTimeRange(self.field, self.start_days, self.end_days)
            selector.filter(f)
        else:
            logging.error('%s: time field is not found, but time_filter is set', selector.tablename)
        return selector
        
class NumFilterConfig:
    """根据数值过滤, 取最大/最小"""
    def __init__(self, field, method: str):
        self.field = field
        self.method = method
    
    def apply(self, selector: RowSelector):
        if self.method == 'min':
            selector.min(self.field)
        elif self.method == 'max':
            selector.max(self.field)
        else:
            logging.error('unknown method %s', self.method)
        return selector
        
class ValueFilterConfig:
    """根据字段取值过滤"""
    
    FIELD_FILTER_CLASS = RowFieldFilter
    
    def __init__(self, field=None, value=None, operator='eq', **kwargs):
        # 要判断的字段
        self.field = field
        # 对比值
        self.value = value
        # 运算符, gt, lt, gte, lte, contains, in, regex, eq
        self.operator = operator
        self._and = kwargs.get('and', [])
        self._or = kwargs.get('or', [])
        self._not = kwargs.get('not', {})
    
    @classmethod
    def parseConfig(cls, **config):
        configs = []
        # 等于运算符可以同时支持写多个字段
        if config.get('operator', 'eq') == 'eq' and 'field' not in config and 'not' not in config and 'and' not in config and 'or' not in config:
            for k, v in config.items():
                if k not in ['and', 'or', 'not', 'operator', 'value']:
                    tmp = {
                        'field': k,
                        'value': v
                    }
                    tmp.update(config)
                    logging.info(tmp)
                    configs.append(cls(**tmp))
        else:
            configs.append(cls(**config))
        return configs
    
    def getFilter(self) -> RowFilter:
        # and条件
        if self._and:
            field_filter: Optional[RowFilter] = None
            for item in self._and:
                cf = self.__class__(**item).getFilter()
                if field_filter:
                    field_filter = field_filter & cf
                else:
                    field_filter = cf
            return field_filter  # type: ignore
        elif self._or:
            field_filter: Optional[RowFilter] = None
            for item in self._or:
                logging.info(item)
                cf = self.__class__(**item).getFilter()
                if field_filter:
                    field_filter = field_filter | cf
                else:
                    field_filter = cf
            return field_filter # type: ignore
        elif self._not:
            field_filter: Optional[RowFilter] = None
            cf = self.__class__(**self._not).getFilter()
            return ~cf
        elif not self.field:
            raise ValueError('no field is specified')
        field_filter = self.FIELD_FILTER_CLASS(self.field)
        
        if self.operator in ('gt', 'gte'):
            field_filter.gt(self.value)
        elif self.operator in ('lt', 'lte'):
            field_filter.lt(self.value)
        elif self.operator == 'eq':
            field_filter.equal(self.value)
        elif self.operator == 'contains':
            field_filter.contain(self.value)
        elif self.operator == 'in':
            if isinstance(self.value, str):
                field_filter.is_in(json.loads(self.value))
            else:
                field_filter.is_in(self.value)
        elif self.operator == 'regex':
            field_filter.regex(self.value)
        elif self.operator == 'has_symptom':
            field_filter.hasSymptom(self.value)
        elif self.operator == 'prefix':
            field_filter.prefixWith(self.value)
        elif self.operator == 'suffix':
            field_filter.suffixWith(self.value)
        else:
            raise ValueError(f'unknown operator {self.operator}')
        return field_filter
    
    def apply(self, selector: RowSelector):
        """将过滤条件应用到selector上"""
        f = self.getFilter()
        selector.filter(f)
        return selector
    
class RowSelectorConfig:
    
    VALUE_FILTER_CLASS = ValueFilterConfig
    
    def __init__(self, ext_fields, **config):
        # 当前已经提取过的其他字段
        self.ext_fields = ext_fields
        # 时间过滤设置
        self.time_filters = []
        for item in config.get('time_filter', []):
            self.time_filters.append(TimeFilterConfig(**item))
            
        # 取第几次的数据, 默认首次
        self.index = config.get('index')
        
        # 取某个字段的最大值或最小值
        self.num_filter = None if not config.get('num_filter') else NumFilterConfig(**config['num_filter'])
        
        # 字段取值过滤
        self.valueFilters = []
        for item in config.get('value_filter', []):
            self.valueFilters.extend(self.VALUE_FILTER_CLASS.parseConfig(**item))     
    
    def apply(self, selector: RowSelector):
        """将配置条件应用到selector上"""
        for f in self.time_filters:
            f.apply(selector)
        
        if self.num_filter:
            self.num_filter.apply(selector)
        
        for f in self.valueFilters:
            f.apply(selector)
        
        selector.setIndex(self.index)
        return selector
    
class FieldPath:
    """字段路径和字段名称, 字段名称仅当存在子字段时需要
    """
    def __init__(self, path, name=''):
        self.path = path
        self.name = name
                
class FieldSelectorConfig:
    """确定行之后如何选择字段"""
    
    def __init__(self, field_path, drop_null=True):
        self.field_path = self.analyzeFieldPath(field_path)
        self.drop_null = drop_null    
    
    def analyzeFieldPath(self, field_path) -> List[FieldPath]:
        """解析配置的字段路径
        """
        if isinstance(field_path, str):
            return [FieldPath(path=field_path)]
        elif isinstance(field_path, list):
            path = []
            for item in field_path:
                if isinstance(item, str):
                    path.append(FieldPath(item))
                else:
                    path.append(FieldPath(path=item['path'], name=item.get('name', item['path'])))
            return path
        else:
            return []
        
    def getFieldPathForSelector(self):
        """生成给FieldSelector用的field_path
        """
        return [item.path.split('.') for item in self.field_path]

    def translate(self, result: FieldResult):
        """转换FieldResult中的名称
        """
        if not result:
            return result
        # 仅当存在二级字段时需要转换
        if len(self.field_path) > 1 and isinstance(result.value, list):
            name_map = {item.path: item.name for item in self.field_path}
            res = []
            for item in result.value:
                tmp = {}
                for k, v in item.items():
                    rel_key = name_map[k]
                    if not tmp.get(rel_key) and v:
                        tmp[rel_key] = v
                res.append(tmp)
            result.value = res
        return result
        

class IndicatorConfig(IndicatorConfigBase):
    """一个指标的配置"""
    
    def __init__(self, key: str, name: str, rule: dict):
        super().__init__(key, name)
        self.rule = rule

class ConfigFieldExtractor(FieldExtractor):
    """基于配置文件的字段提取"""
    
    def __init__(self, case: DataSet, ext_fields, config_obj: dict):
        # 从project_indicator_config表取出来的rule字段对应的json
        self.config_obj = config_obj
        self.table = config_obj.get('table')
        # 如何选择行
        # 这里是一个trick, index配置在上一层也算
        if 'index' in config_obj and 'row_selector' in config_obj:
            config_obj['row_selector']['index'] = config_obj['index']
        self.row_selector_config = None if not config_obj.get('row_selector') else RowSelectorConfig(ext_fields=ext_fields, **config_obj['row_selector'])
        # 如何选择字段
        self.field_selector_config = None if not config_obj.get('field_selector') else FieldSelectorConfig(**config_obj['field_selector'])
        selector: Optional[RowSelector] = RowSelector.getRowSelector(self.Table)
        if not selector:
            logging.error('get row selector failed, table is %s', self.Table)
            return None
        self.field_type = self.config_obj.get('field_type')
        # 不指定字段类型时推测字段类型
        if self.field_selector_config and len(self.field_selector_config.field_path) > 1:
            if self.row_selector_config and self.row_selector_config.index is not None:
                self.field_type = 'dict'
            else:
                self.field_type = 'record'
        else:
            self.field_type = 'str'
        super().__init__(case, ext_fields, selector) 
    
    @property
    def Table(self):
        return self.config_obj.get('table')
    
    def extract(self, target_time=None, start_hours=7*24, end_hours=7*24) -> FieldResult:
        """提取字段并返回

        Args:
            target_time (datetime, optional): 参照时间, 如果提供将选择距此时间最近的一条记录的值. Defaults to None.
            start_hours (int, optional): 若target_time不为空则只保留晚于target_time前start_hours个小时的数据. Defaults to 7*24.
            end_hours (int, optional): 若target_time不为空, 则只保留早于target_time之后end_hours小时之内的数据. Defaults to 7*24.
        """
        if self.row_selector_config:
            self.row_selector_config.apply(self.selector)
        
        self.setSelectorTimeRange(target_time=target_time, start_hours=start_hours, end_hours=end_hours)

        # 不指定字段则表示判断是否存在, 存在则为'是', 不存在为'否'
        if not self.field_selector_config:
            field = FieldSelector(self.selector, field_type=self.getFieldType(self.field_type))
        else:
            field = FieldSelector(self.selector, self.field_selector_config.getFieldPathForSelector(), self.getFieldType(self.field_type), drop_null=self.field_selector_config.drop_null)
        result = field.getSuggestion(self.case, ext_fields=self.ext_fields)
        if self.field_selector_config:
            result = self.field_selector_config.translate(result)
        if result:
            result.field_type = self.field_type
        return result
    
    @classmethod
    def extractIndicator(cls, indicators: List[IndicatorConfig], dataset: DataSet, 
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
            unique_tables (Iterable[str], optional): 在当前dataset中只会存在最多一条记录的表名. Defaults to ().
            time_fields (dict): 指定每个表的时间字段, 只有指定了时间字段设置index才有意义, 因为要根据时间来排序. 指定了时间字段后可以选择距离目标时间最近的数据
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
            extractor = ConfigFieldExtractor(dataset, ext_fields=ext_fields, config_obj=indicator.rule)
            extractor.setTimeField(time_fields.get(extractor.selector.tablename))
            val = extractor.extract(target_time=target_time, start_hours=start_hours, end_hours=end_hours)
            if val is not None:
                result[indicator.key] = val
                ext_fields[indicator.key] = val.value
                logging.debug('%s: %s', indicator.key, val.value)
        return result

        
        