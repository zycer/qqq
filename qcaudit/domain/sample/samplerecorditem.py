#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 11:37:45

'''
from typing import Tuple

from qcaudit.domain.domainbase import DomainBase


class SampleRecordItem(DomainBase):
    """抽取到的明细项目
    Fields:
        id:
        recordId: samplerecord表的id
        caseId: 对应的病历号,如果是运行病历对应的是快照的id
        expertId: 被分配的专家id
        auditType: 冗余一次方便join
    """
    TABLE_NAME = 'sample_record_item'

    def __init__(self, model, caseModel=None, auditRecord=None):
        super().__init__(model)
        self.caseModel = caseModel
        self.auditRecord = auditRecord
    
    def expunge(self, session):
        self.expungeInstance(session, self.model, self.caseModel, self.auditRecord)
    
    def assignExpert(self, expertId, expertName, isMannalAssigned=0):
        """分配专家
        """
        self.model.expertId = expertId
        self.model.expertName = expertName
        self.model.isMannalAssigned = isMannalAssigned
        return self.model.recordId

    def getAssignExpert(self):
        return (self.model.expertId, self.model.expertName)
