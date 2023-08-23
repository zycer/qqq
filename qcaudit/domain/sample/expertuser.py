#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 11:38:08

'''

from qcaudit.domain.domainbase import DomainBase


class ExpertUser(DomainBase):
    """
        质控专家
        字段:
            audit_type: 审核类型
            user_id: 用户id
            user_name: 用户姓名
    """

    TABLE_NAME = 'expert_user'

    def __init__(self, model):
        self.model = model
        self.department = ""

    @property
    def userId(self):
        return self.model.userId

    @property
    def userName(self):
        return self.model.userName

    def setDepartment(self, dept):
        self.department = dept
