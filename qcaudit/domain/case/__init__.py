#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-18 09:39:17

'''

from qcaudit.domain.case.caserepository import CaseRepository
from qcaudit.domain.case.emrrepository import EmrRepository
from qcaudit.domain.case.emrsvc import EmrService
from qcaudit.domain.case.orderrepository import OrderRepository


class CaseFactory(object):
    
    @classmethod
    def getCaseRepository(cls, context, auditType) -> CaseRepository:
        return CaseRepository(context, auditType)
    
    @classmethod
    def getEmrRepository(cls, context, auditType) -> EmrRepository:
        return EmrRepository(context, auditType)
    
    @classmethod
    def getEmrService(cls, context, auditType) -> EmrService:
        return EmrService(context, auditType)
    
    @classmethod
    def getOrderRepository(cls, context, auditType) -> OrderRepository:
        return OrderRepository(context, auditType)