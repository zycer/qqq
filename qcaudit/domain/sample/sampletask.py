#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: sampletask.py
@time: 2022/12/20 18:14
@desc:
"""
from qcaudit.domain.domainbase import DomainBase


class SampleFilterModel(DomainBase):
    """
    抽取条件表
    """
    TABLE_NAME = 'sample_filter'

    def __init__(self, model):
        super().__init__(model)


class SampleTaskModel(DomainBase):
    """
    抽取定时任务表
    """
    TABLE_NAME = 'sample_task'

    def __init__(self, model):
        super().__init__(model)
