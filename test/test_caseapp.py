#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 18:19:28

'''
import logging

from qcaudit.common.const import AUDIT_TYPE_HOSPITAL
from qcaudit.context import Context
from qcaudit.app import Application
from qcaudit.domain.case.req import GetCaseListRequest, GetEmrListRequest
import unittest
import os

class TestCaseApplication(unittest.TestCase):

    def setUp(self):
        mysqlUrl = os.environ.get('MYSQL_URL', 'mysql+pymysql://root:rxthinkingmysql@192.168.100.40:31444/qcmanager_v3?charset=utf8mb4')
        mongoUrl = os.environ.get('MONGO_URL', 'mongodb://192.168.101.159')
        self.app = Application(mysqlUrl, mongoUrl)

        self.context = Context(self.app)

    def test_getCaseList(self):
        req = GetCaseListRequest(
            caseId='7948899',
            start=0,
            size=10
        )
        r = list(self.context.getCaseApplication(AUDIT_TYPE_HOSPITAL).getCaseList(req))
        assert(len(r) > 0)

    def test_getCaseListBytag(self):
        req = GetCaseListRequest(
            tags=['dead', 'hard'],
            start=0,
            size=10
        )
        r = list(self.context.getCaseApplication(AUDIT_TYPE_HOSPITAL).getCaseList(req))
        for item in r:
            print(item.tags, item.caseId)
        assert(len(r) > 0)

    def test_getCaseDetail(self):
        c = self.context.getCaseApplication(AUDIT_TYPE_HOSPITAL).getCaseDetail('7948899')
        assert(c.caseId is not None)

    def test_getCaseEmr(self):
        req = GetEmrListRequest(
            caseId='7948899'
        )
        r = list(self.context.getCaseApplication(AUDIT_TYPE_HOSPITAL).getCaseEmr(req))
        assert(len(r) > 0)

    def test_calculateCaseScore(self):
        r = self.context.getAuditApplication(AUDIT_TYPE_HOSPITAL).calculateCaseScore('7948899', 22)
        print(r.isSuccess)
        print(r.message)
        assert(r.isSuccess == True)

    def test_getReviewers(self):
        r = self.context.getAuditApplication(AUDIT_TYPE_HOSPITAL).getReviewers()
        print(type(r))

        assert(len(r) > 0)
