#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 11:53:59

'''
from typing import List
from qcaudit.domain.domainsvc import DomainService
from qcaudit.domain.case.case import CaseDoctor

class EmrService(DomainService):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)

    def getDoctors(self, caseId) -> List[CaseDoctor]:
        """获取文书中的医生

        Args:
            caseId ([type]): [description]

        Returns:
            List[CaseDoctor]: [description]
        """
        raise NotImplementedError()
