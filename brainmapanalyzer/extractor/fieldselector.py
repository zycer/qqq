#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
import logging
from typing import Callable, List
from brainmapanalyzer.dataset import DataSet
from brainmapanalyzer.utils import findField
from dateutil.parser import parse
from datetime import datetime
from brainmapanalyzer.extractor.fieldextractor import FieldResult, FieldSourceInfo

class FieldSelector(object):
    """字段选择器, 从行中选择出需要的字段
    """

    def __init__(self, row_selector, field_path=None, field_type=list, drop_null=False, extract_func=None):
        # 字段的Python类型
        self.field_type = field_type
        self.row_selector = row_selector
        self.field_type = field_type
        # field_path可以为多个, 多个的时候field_type必须是list
        self.field_path = []
        
        if field_path:
            if isinstance(field_path, str):
                self.field_path = [field_path.split('.')]
            elif isinstance(field_path, list):
                if isinstance(field_path[0], list):
                    self.field_path = list(field_path)
                else:
                    self.field_path.append(field_path)
            else:
                raise ValueError('field_path must be string or list')
        else:
            # 不指定提取字段视为判断有无, 结果类型为bool
            self.field_type = bool
        # 指定了不止一个path, 字段类型只能是list和dict
        if len(self.field_path) > 1 and self.field_type is not list and self.field_type is not dict:
            raise ValueError('field_path can specify multi field only when type is dict or list')
        self._value_extract_func: Callable = extract_func # type: ignore
        # 忽略null值
        self._drop_null = drop_null

    def convertValue(self, value):
        '''将从数据库中提取到的值转换成想要的类型
        '''
        logging.debug('convert %s to %s', value, self.field_type)
        if self.field_type is list:
            return value
        if isinstance(value, self.field_type):
            return value
        if isinstance(value, list):
            if len(value) > 0:
                if len(value) > 1:
                    logging.warning('want one value, but got %d value, use the first one', len(value))
                return self.convertValue(value[0])
            else:
                return None
        else:
            if self.field_type is datetime:
                logging.info('%s: %s', self.field_path, value)
                return parse(value)
            elif self.field_type is float:
                return float(value)
            elif self.field_type is int:
                return int(value)
            elif self.field_type is str:
                return str(value)
            else:
                raise ValueError('unknown type')

    def extract(self, func):
        self._value_extract_func = func
        return self

    def before(self, dt):
        self.row_selector.before(dt)
        return self

    def after(self, dt):
        self.row_selector.after(dt)
        return self

    def first(self):
        self.row_selector.first()
        return self

    def last(self):
        self.row_selector.last()
        return self
    
    def getValue(self, row, field_path):
        """从一行数据中提取字段
        """
        return findField(row, field_path)

    def getSuggestion(self, dataset: DataSet, ext_fields: dict = None) -> FieldResult:
        '''获取字段的值

        Args:
            case: 所有的数据集合
            
        '''
        ext_fields = ext_fields or {}
        rows = self.row_selector.select(dataset, ext_fields)
        if not rows:
            logging.debug('cannot get rows for field, %s', self.field_path)
        # 不指定字段提取规则时即为判断是否存在, 类型为bool
        if not self.field_path and not self._value_extract_func:
            if not rows:
                return FieldResult(False)
            else:
                return FieldResult(True)
        sug_result: List[FieldResult] = []
        logging.info(rows)
        for row in rows:
            # 不存在二级字段
            if len(self.field_path) <= 1:
                r = FieldResult(None)
                #logging.info('find %s from %s', self.field_path, row.obj)
                if self.field_path:
                    tmp = self.getValue(row, self.field_path[0])
                    r.addSource(FieldSourceInfo(self.row_selector.tablename, self.field_path[0], self.row_selector.getID(row)))
                else:
                    tmp = self._value_extract_func(row)
                    r.addSource(FieldSourceInfo(table=self.row_selector.tablename, id=self.row_selector.getID(row)))
                if self._drop_null and tmp is None:
                    continue
                try:
                    converted_value = self.convertValue(tmp)
                    if isinstance(converted_value, list):
                        for item in converted_value:
                            sug_result.append(FieldResult(item, list(r.source)))
                    else:
                        r.value = converted_value
                        sug_result.append(r)
                    logging.debug('got field value %s', converted_value)
                except Exception as e:
                    logging.exception(e)
                    logging.error(str(tmp))
                    continue
            else: # 存在二级字段, 忽略convert, 返回原始数据
                value = {
                    '.'.join(path): self.getValue(row, path) for path in self.field_path
                }
                # 二级字段全部是str类型
                value = {
                    k: '\n'.join([str(vv) for vv in v]) for k, v in value.items()
                }
                sug_result.append(FieldResult(value=value))
                    
        # 没有提取到结果
        if not sug_result:
            return None
        elif self.field_type is list:
            value = [item.value for item in sug_result]
            sources = []
            for item in sug_result:
                sources.extend(item.source)
            return FieldResult(value, sources)  
        elif len(sug_result) == 1:
            return sug_result[0]
        else:
            # 有多条满足条件的结果, 如果类型是字符串则用\n合并,否则只取第一条
            if self.field_type is str:
                value = '\n'.join([str(s.value) for s in sug_result if s.value])
                sources = []
                for item in sug_result:
                    sources.extend(item.source)
                return FieldResult(value, sources)
            else:
                return sug_result[0]
