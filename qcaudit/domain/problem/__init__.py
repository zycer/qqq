#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-18 09:45:28

'''

from qcaudit.domain.problem.problemrepository import ProblemRepository


class ProblemFactory:
    
    @classmethod
    def getProblemRespository(cls, context, auditType) -> ProblemRepository:
        return ProblemRepository(context, auditType)