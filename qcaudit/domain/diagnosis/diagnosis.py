#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   diagnosis.py
@Time    :   2023/06/27 10:20:45
@Author  :   zhangda 
@Desc    :   None
'''


from qcaudit.domain.domainbase import DomainBase


class DiagnosisInfo(DomainBase):

	TABLE_NAME = 'diagnosis_info'


class DiagnosisDict(DomainBase):

	TABLE_NAME = 'diagnosis_origin_dict'
