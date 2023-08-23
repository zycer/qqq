#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 15:47:52

'''
from dataclasses import dataclass

from qcaudit.domain.req import ListRequestBase, SortField


@dataclass
class GetCheckHistoryListRequest(ListRequestBase):
    """获取质控日志列表

    Args:
        ListRequestBase ([type]): [description]
    """

    caseId: str = ''
    auditType: str = ''
    auditStep: str = ''

    def __post_init__(self):
        if not self.sortFields:
            self.sortFields.append(
                SortField(field='created_at')
            )

    def applyFilter(self, query, connection):
        model = connection['checkHistory']
        if self.caseId:
            query = query.filter(
                model.caseId == self.caseId
            )
        if self.auditType:
            query = query.filter(
                model.auditType == self.auditType
            )
        # if self.auditStep:
        #     query = query.filter(
        #         model.auditStep == self.auditStep
        #     )
        return query

    def applySort(self, query, connection):
        model = connection['checkHistory']
        query = query.order_by(model.created_at.desc())
        return query
