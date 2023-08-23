#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-18 09:28:27

'''
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL
from qcaudit.domain.audit.auditrecordrepository import AuditRecordRepository
from qcaudit.domain.audit.checkhistoryrepository import CheckHistoryRepository
from qcaudit.domain.audit.refusedetailrepository import RefuseDetailRepository
from qcaudit.domain.audit.refusehistoryrepository import RefuseHistoryRepository

class AuditFactory(object):
    
    @classmethod
    def getAuditRecordRepository(cls, context, auditType):
        return AuditRecordRepository(context, auditType)
    
    @classmethod
    def getCheckHistoryRepository(cls, context, auditType):
        return CheckHistoryRepository(context, auditType)
    
    @classmethod
    def getRefuseHistoryRepository(cls, context, auditType):
        return RefuseHistoryRepository(context, auditType)

    @classmethod
    def getRefuseDetailRepository(cls, context, auditType):
        return RefuseDetailRepository(context, auditType)
