#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 17:57:25

'''


from typing import Any, Iterable, List

from qcaudit.app import Application
from qcaudit.domain.audit.checkhistoryrepository import CheckHistoryRepository
from qcaudit.domain.user.user import User


class ApplicationBase(object):

    def __init__(self, app: Application, auditType: str):
        self.app = app
        self.auditType = auditType
        self._checkHistoryRepository = CheckHistoryRepository(app, auditType)
    
    def expunge(self, session, dataList: List[Any]) -> List[Any]:
        dataList = dataList or []
        result = []
        for item in dataList:
            if item:
                item.expunge(session)
            result.append(item)
        return result

    def ensureUserName(self, operatorId: str, operatorName: str = ''):
        """用户姓名为空时补齐用户姓名

        Args:
            operatorId (str): [description]
            operatorName (str): [description]
        """
        User.DATABASE = self.app.iamDatabase
        u = User.getById(self.app.mongo, operatorId)
        name = u.name if u.name else operatorName
        return operatorId, name, operatorName

    def getDeptPermission(self, operatorId):
        if not operatorId:
            return ("", list())
        User.DATABASE = self.app.iamDatabase
        u = User.getUserCaseDeptPermissions(self.app.mongo, operatorId)
        return u
