#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-18 10:04:24

'''

from qcaudit.domain.user.userrepository import UserRepository


class UserFactory:
    
    @classmethod
    def getUserRepository(cls, context, auditType):
        return UserRepository(context, auditType)