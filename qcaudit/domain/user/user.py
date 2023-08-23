#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-09 14:55:46

'''

from qcaudit.domain.domainbase import MongoDomainBase


class User(MongoDomainBase):

    DATABASE = 'iam'
    COLLECTION = 'user'

    @classmethod
    def getUserCaseDeptPermissions(cls, client, uid):
        col = cls.getCollection(client)
        result = col.find_one({"_id": uid})
        if not result:
            return "", list()
        dept_perms = result.get('deptPerms')
        if dept_perms:
            return dept_perms.get('type', ''), dept_perms.get('departments', list())
        return "", list()

    @classmethod
    def getUserDepartment(cls, client, uid):
        col = cls.getCollection(client)
        result = col.find_one({"_id": uid})
        if not result:
            return ""
        info = result.get('info')
        if info:
            return info.get('department')
        return ""
