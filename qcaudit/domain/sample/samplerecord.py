#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 11:37:24

'''

from qcaudit.domain.domainbase import DomainBase


class SampleRecord(DomainBase):
    TABLE_NAME = 'sample_record'
    
    # 平均分配
    ASSIGN_TYPE_AVG = 'avg'
    # 自动分配
    ASSIGN_TYPE_AUTO = 'auto'

    """抽取历史记录
    Fields:
        id: 
        auditType: 审核类型
        operatorId: 
        operatorName: 抽取人姓名
        createdAt: 抽取时间
        isAssigned: 是否已经分配
    """

    def __init__(self, model):
        super().__init__(model)

    def getId(self):
        return self.model.id

    @property
    def sampleBy(self):
        return self.model.sampleBy

    @property
    def sampledCount(self):
        return self.model.sampledCount or 0

    def addSampleBy(self, data):
        if self.model.sampleBy:
            if data not in self.model.sampleBy.split(','):
                self.model.sampleBy += "," + data
        else:
            self.model.sampleBy = data

    def setSampledCount(self, count):
        self.model.sampledCount = count

    def setLastOperationId(self, op):
        self.model.lastOperation = op

    def submit(self):
        self.model.submit_flag = 1
