#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@iyoudoctor.com

'''
from datetime import datetime
from typing import Iterable
from brainmapanalyzer.utils import findField, findOneField, parseDate, parseTime
import re
import logging
from dateutil.parser import parse

NOT_SET_VALUE = object()


class RowFilter(object):

    def __and__(self, other):
        return AndRowFilter(filters=[self, other])

    def __or__(self, other):
        return OrRowFilter(filters=[self, other])

    def __invert__(self):
        return InvertRowFilter(f=self)

    def check(self, row, ext_fields: dict=None):
        '''检查过滤条件是否满足

        Args:
            row ([type]): 一条数据
            ext_fields: 已经提取出来的其他字段
        Raises:
            NotImplementedError: [description]
        '''

        raise NotImplementedError()


class FunctionFilter(RowFilter):
    """
    基于一个函数来判断当前行是否满足条件, 函数的返回值必须是True或false
    """

    def __init__(self, func):
        self.func = func

    def check(self, row, ext_fields:dict = None):
        ext_fields = ext_fields or {}
        return self.func(row, ext_fields)


class InvertRowFilter(RowFilter):
    '''给过滤器取反
    '''

    def __init__(self, f):
        self._filter = f

    def check(self, row, ext_fields: dict = None):
        ext_fields = ext_fields or {}
        if self._filter.check(row, ext_fields):
            return False
        else:
            return True


class OrRowFilter(RowFilter):
    '''过滤器求或
    '''

    def __init__(self, filters=None):
        self._filters = filters or []

    def check(self, row, ext_fields: dict = None):
        ext_fields = ext_fields or {}
        if not self._filters:
            return True
        for f in self._filters:
            if f.check(row, ext_fields):
                return True
        return False


class AndRowFilter(RowFilter):
    '''过滤器求与
    '''

    def __init__(self, filters=None):
        self._filters = filters or []

    def check(self, row, ext_fields: dict = None):
        ext_fields = ext_fields or {}
        if not self._filters:
            return True
        for f in self._filters:
            if not f.check(row, ext_fields):
                return False
        return True


class TimeRange:
    """表示字段位于某一个时间范围内"""
    def __init__(self, ref: str, start=0, end=0):
        """
        Args:
            ref (str): 参考时间字段
            start (int, optional): 起始时间在参考时间前多少秒. Defaults to 0.
            end (int, optional): 起始时间在参考时间后多少秒. Defaults to 0.
        """
        self.ref = ref
        if self.ref.startswith('${'):
            self.ref = self.ref[2:-1]
        self.start = start
        self.end = end

    def getRefValue(self, ext_fields):
        """支持引用其他变量
        """
        if ext_fields:
            return findOneField(ext_fields, self.ref)
        else:
            return None

    def match(self, value, ext_fields: dict = None):
        """检查给定值是否在区间范围内
        """
        logging.debug('timerange.match: %s', ext_fields)
        ext_fields = ext_fields or {}
        ref_value = self.getRefValue(ext_fields)
        if ref_value is None:
            return False
        logging.debug('ref_value: %s', ref_value)
        ref_time = parseTime(ref_value)
        if ref_time is None:
            return False
        target_time = parseTime(value)
        if target_time is None:
            return False
        ts = (target_time - ref_time).total_seconds()
        logging.debug('target: %s, ref_value: %s, ext_fields: %s, ts: %s, start: %s, end: %s',
                      target_time, ref_value, ext_fields, ts, self.start, self.end)
        if ts < -self.start:
            return False
        if ts > self.end:
            return False
        return True


class RowFieldFilter(RowFilter):

    def __init__(self, field_path, equal_value=NOT_SET_VALUE,
                 contain_value=NOT_SET_VALUE,
                 gt_value=NOT_SET_VALUE, lt_value=NOT_SET_VALUE,
                 regex=NOT_SET_VALUE, match_all=False, is_in=NOT_SET_VALUE,
                 gte_value=NOT_SET_VALUE, lte_value=NOT_SET_VALUE,
                 func=None, time_range=NOT_SET_VALUE, prefix_value=NOT_SET_VALUE,
                 suffix_value=NOT_SET_VALUE):
        '''

        Args:
            field_path (str): 字段路径
            equal_value (object, optional): Defaults to NOT_SET_VALUE. 与指定值相等
            contain_value (object, optional): Defaults to NOT_SET_VALUE. 包含指定值
            gt_value (object, optional): Defaults to NOT_SET_VALUE. 大于指定
            lt_value (object, optional): Defaults to NotImplemented. 小于指定值
            regex (str, optional): Defaults to NOT_SET_VALUE.  正则表达式可以搜索到pat.search() is not None
            match_all (bool, optional): Defaults to False. 字段有多个值的时候需要全匹配还是匹配任一个就行
            is_in (iterable, optional): Defaults to NOT_SET_VALUE. 当前值包含在指定的list中
            func (function, optional): Defaults to None. 提供一个函数,返回True则接受
            以上用于判断字段是否符合条件的字段只能有一个.
        '''

        self.field_path = field_path
        self._equal_value = equal_value
        self._contain_value = contain_value
        self._gt_value = gt_value
        self._lt_value = lt_value
        self._gte_value = gte_value
        self._lte_value = lte_value
        if regex is not NOT_SET_VALUE:
            self._regex_pat = re.compile(regex)
        else:
            self._regex_pat = None
        # True时如果field_path指向的字段有多个值,则需要全部满足,否则只需要一个满足即可
        self._match_all = match_all
        self._is_in = is_in
        self._func = func
        self._time_range: TimeRange = time_range # type: ignore
        # 以prefix_value开头
        self._prefix_value = prefix_value
        # 以suffix_value结尾
        self._suffix_value = suffix_value

    def func(self, value):
        """提供一个函数来判断当前行是否符合条件, 函数的输入参数为row和ext_fields

            def func(row, ext_fields=None):
                return True
        """
        self._func = value
        return self

    def is_in(self, value: Iterable):
        """目标字段在给定的值域范围内, value是一个可迭代对象"""
        self._is_in = value
        return self

    def equal(self, value):
        """等于"""
        self._equal_value = value
        return self

    def contain(self, value):
        """目标字段包含value的值, 仅针对字符串"""
        self._contain_value = value
        return self

    def gt(self, value, equal=False):
        """大于"""
        if equal:
            self._gte_value = value
        else:
            self._gt_value = value
        return self

    def lt(self, value, equal=False):
        """目标字段需要小于value的值"""
        if equal:
            self._lte_value = value
        else:
            self._lt_value = value
        return self

    def regex(self, regex):
        """目标字段需要匹配指定的正则表达式"""
        self._regex_pat = re.compile(regex)
        return self

    def prefixWith(self, prefix):
        """以prefix开头
        """
        self._prefix_value = prefix

    def suffixWith(self, suffix):
        """以suffix结尾
        """
        self._suffix_value = suffix

    def hasSymptom(self, regex):
        """包含对应正则表达式的症状
        """
        self._func = CheckSymptom(regex)
        return self

    def translate(self, value, row, ext_fields):
        """
        value中支持 ${variable}这种写法来引用其他变量, 将从当前行或已提取的其他字段中解析出对应的字段值用于最终的比较
        Args:
            value : 表达式对比的值
            row (dict): 当前整个数据行
            ext_fields (dict): 已经提取出来的其他字段, 或者在整个dataset中可以唯一的字段
        """
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            ret = findOneField(row, value[2:-1]) or findOneField(ext_fields, value[2:-1])
            logging.debug('%s translated to %s, ext_fields: %s', value, ret, ext_fields)
            return ret
        else:
            return value

    def inTimeRange(self, ref, start_days=0, end_days=0):
        """位于ref字段对应时间的前start_days天和后end_days天之间
        """
        self._time_range = TimeRange(ref, int(start_days) * 86400, int(end_days)*86400)
        return self

    def match(self, value, row, ext_fields: dict = None):
        if value is None:
            return False
        ext_fields = ext_fields or {}
        logging.debug('match: %s, %s, %s', self.__dict__, value, ext_fields)
        try:
            if self._equal_value is not NOT_SET_VALUE:
                rval = self.translate(self._equal_value, row, ext_fields)
                if rval is None:
                    return False
                # TODO: 应该匹配双方的精度去比较
                if isinstance(rval, datetime):
                    return parseDate(value) == rval.date()
                return self.translate(self._equal_value, row, ext_fields) == value
            elif self._contain_value is not NOT_SET_VALUE:
                rval = self.translate(self._contain_value, row, ext_fields)
                if rval is None or value is None:
                    return False
                return rval in value
            elif self._regex_pat is not None:
                return self._regex_pat.search(value)
            elif self._gt_value is not NOT_SET_VALUE:
                rval = self.translate(self._gt_value, row, ext_fields)
                if rval is None or value is None:
                    return False
                if isinstance(rval, datetime) or isinstance(value, datetime):
                    return parseTime(value) > parseTime(rval) # type: ignore
                return float(value) > float(rval) # type: ignore
            elif self._gte_value is not NOT_SET_VALUE:
                rval = self.translate(self._gte_value, row, ext_fields)
                if rval is None:
                    return False
                if isinstance(rval, datetime) or isinstance(value, datetime):
                    return parseTime(value) >= parseTime(rval)  # type: ignore
                return int(value) >= int(rval) # type: ignore
            elif self._lte_value is not NOT_SET_VALUE:
                rval = self.translate(self._lte_value, row, ext_fields)
                if rval is None:
                    return False
                if isinstance(rval, datetime) or isinstance(value, datetime):
                    return parseTime(value) <= parseTime(rval)  # type: ignore
                return int(value) <= int(rval)  # type: ignore
            elif self._lt_value is not NOT_SET_VALUE:
                rval = self.translate(self._lt_value, row, ext_fields)
                if rval is None:
                    return False
                if isinstance(rval, datetime) or isinstance(value, datetime):
                    return parseTime(value) < parseTime(rval)  # type: ignore
                return float(value) < float(rval)  # type: ignore
            elif self._is_in is not NOT_SET_VALUE:
                return value in self._is_in
            elif self._func is not None:
                return self._func(value)
            elif self._time_range is not NOT_SET_VALUE:
                return self._time_range.match(value, ext_fields)
            elif self._prefix_value is not NOT_SET_VALUE:
                return str(value).startswith(self._prefix_value)
            elif self._suffix_value is not NOT_SET_VALUE:
                return str(value).endswith(self._suffix_value)
            else:
                return True
        except Exception as e:
            logging.exception(e)
            return False

    def check(self, row, ext_fields: dict = None):
        ext_fields = ext_fields or {}
        # TODO: check value_type
        result = findField(row, self.field_path)
        if not result:
            return False
        if not self._match_all:
            for value in result:
                if self.match(value, row, ext_fields):
                    return True
            return False
        else:
            for value in result:
                if not self.match(value, row, ext_fields):
                    return False
            return True


class HasSymptomFilter(RowFieldFilter):
    '''检查症状是否存在
    '''

    def __init__(self, regex, field='text'):
        super(HasSymptomFilter, self).__init__(field_path=field, func=CheckSymptom(regex))


class CheckSymptom(object):
    '''对应的字段不仅匹配正则表达式,而且所在短句(逗号或句号分割的句子)中不包含否定词
    '''

    def __init__(self, regex):
        self._regex = re.compile(regex)

    def __call__(self, value, ext_fields: dict = None):
        ext_fields = ext_fields or {}
        if not isinstance(value, str):
            raise ValueError('Only str is supported')

        result = self._regex.search(value)
        if not result:
            return False

        # 正则匹配的起始和结束位置
        start_pos, end_pos = result.span()
        sen_start_pos, sen_end_pos = start_pos, end_pos

        # 找到命中的词语所在短句
        for i in range(start_pos, -1, -1):
            if i == 0 or value[i] in (u',', u'，', u'。', u';', u'；'):
                sen_start_pos = i
                break
        text_len = len(value)
        for i in range(end_pos, text_len, 1):
            if i == text_len - 1 or value[i] in (u',', u'，', u'。', u'；', u';'):
                sen_end_pos = i
                break

        # 查找否定词
        sen = value[sen_start_pos:sen_end_pos + 1]
        if u'无' in sen or u'未见' in sen or u'否认' in sen \
                or u'防' in sen or u'避免' in sen or u'待排' in sen:
            return False
        return True
