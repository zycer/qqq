#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 14:03:36

'''

from qcaudit.domain.domainbase import DomainBase


class Order(DomainBase):
    TABLE_NAME = 'medicalAdvice'

    def __init__(self, model):
        super().__init__(model)


class DrugTag(DomainBase):
    TABLE_NAME = 'drugclasses'

    def __init__(self, model):
        super().__init__(model)
