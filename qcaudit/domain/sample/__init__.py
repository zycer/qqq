#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-18 09:58:01

'''

from qcaudit.domain.sample.expertuserrepository import ExpertUserRepository
from qcaudit.domain.sample.samplerecordrepository import SampleRecordRepository
from qcaudit.domain.sample.samplerecordsvc import SampleRecordService


class SampleFactory:
    
    @classmethod
    def getSampleRecordRepository(cls, context, auditType) -> SampleRecordRepository:
        return SampleRecordRepository(context, auditType)
    
    @classmethod
    def getSampleRecordService(cls, context, auditType) -> SampleRecordService:
        return SampleRecordService(context, auditType)
    
    @classmethod
    def getExpertUserRepository(cls, context, auditType) -> ExpertUserRepository:
        return ExpertUserRepository(context, auditType)
