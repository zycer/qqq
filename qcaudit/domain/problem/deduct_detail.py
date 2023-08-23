#!/usr/bin/env python3


class DeductDetail(object):
    def __init__(self, auditType='', caseId='', docId='', qcItemId=0, problemCount=0, singleScore=0, score=0, operatorName='', createTime='', reason=''):
        self.auditType = auditType or ''
        self.caseId = caseId or ''
        self.docId = docId or ''
        self.qcItemId = qcItemId or 0
        self.problemCount: int = problemCount or 0  # 问题数
        self.singleScore: float = singleScore or 0  # 单处扣分
        self.score: float = score or 0  # 总扣分
        self.operatorName: str = operatorName or ''
        self.createTime: str = createTime or ''
        self.reason: str = reason or ''
