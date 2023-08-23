#!/usr/bin/env python3

from qcaudit.domain.domainbase import DomainBase


class SampleOperation(DomainBase):
    TABLE_NAME = 'sample_operation'

    def __init__(self, model):
        super().__init__(model)

    def setSampledCase(self, caseIds):
        self.model.sampled_case = ','.join(caseIds)


