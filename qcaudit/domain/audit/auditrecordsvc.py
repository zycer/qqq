#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 10:43:08

'''
from qcaudit.domain.audit.auditrecordrepository import AuditRecordRepository
from qcaudit.domain.domainsvc import DomainService

class AuditRecordService(DomainService):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self._auditReposository = AuditRecordRepository(app, auditType)
