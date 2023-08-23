#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 13:11:53

'''
from typing import Iterable, List
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.sample.expertuser import ExpertUser

class ExpertUserRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.model = ExpertUser.getModel(app)
    
    def add(self, session, obj: ExpertUser):
        """添加一个专家

        Args:
            obj (ExpertUser): [description]
        """
        session.add(obj.model)

    def delete(self, session, expertId, caseType):
        """删除一个专家

        Args:
            expertId ([type]): [description]
        """
        session.query(self.model).filter_by(
            auditType=self.auditType,
            caseType=caseType,
            userId=expertId
        ).delete()

    def getList(self, session, caseType) -> List[ExpertUser]:
        """获取专家列表
        """
        result = []
        for row in session.query(self.model).filter_by(
            auditType=self.auditType,
            caseType=caseType
        ):
            result.append(ExpertUser(row))
        return result

