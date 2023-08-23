#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 13:38:52

'''
from typing import Iterable, List
from qcaudit.domain.audit.req import GetCheckHistoryListRequest
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.audit.checkhistory import CheckHistory

import arrow
from sqlalchemy.orm import session

class CheckHistoryRepository(RepositoryBase):

    def getList(self, session, req: GetCheckHistoryListRequest) -> List[CheckHistory]:
        """获取质控日志列表

        Args:
            caseId ([type]): [description]
        """        
        model = CheckHistory.getModel(self.app)
        query = session.query(model)
        query = req.apply(query, self.app.mysqlConnection)
        result = []
        for row in query:
            result.append(CheckHistory(row))
        return result

    def log(self, session, caseId, operatorId, operatorName, action, content, comment, docType='', auditStep='', auditType=""):
        obj = CheckHistory.newObject(self.app)
        obj.setModel(
            auditType=auditType or self.auditType,
            caseId=caseId,
            operatorId=operatorId,
            operatorName=operatorName,
            action=action,
            content=content,
            comment=comment,
            type=docType,
            created_at=arrow.utcnow().to('+08:00').naive,
            auditStep=auditStep
        )
        self.add(session, obj)

    def getReviewer(self, session):
        """审核日志审核人
        """
        model = CheckHistory.getModel(self.app)
        for row in session.query(model.operatorId, model.operatorName).\
                distinct(model.operatorId, model.operatorName).\
                filter_by(auditType=self.auditType):
            yield CheckHistory(row)

    def count(self, session, req: GetCheckHistoryListRequest):
        model = CheckHistory.getModel(self.app)
        req.validate()
        query = session.query(model)
        query = req.applyFilter(query, self.app.mysqlConnection)
        return query.count()
