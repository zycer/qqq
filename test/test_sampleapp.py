#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 18:19:28

'''

from qcaudit.application.sampleapplication import SampleApplication
from qcaudit.common.const import AUDIT_TYPE_HOSPITAL
from qcaudit.context import Context
from qcaudit.app import Application
from qcaudit.domain.case.req import GetCaseListRequest, GetEmrListRequest
import unittest
import os
from qcaudit.domain.sample.req import GetSampleRecordRequest

from qcaudit.domain.sample.samplerecord import SampleRecord

class TestSampleApplication(unittest.TestCase):
    
    def setUp(self):
        mysqlUrl = os.environ.get('MYSQL_URL', 'mysql+pymysql://root:rxthinkingmysql@192.168.100.40:31444/qcmanager_v3?charset=utf8mb4')
        mongoUrl = os.environ.get('MONGO_URL', 'mongodb://192.168.101.159')
        self.app = Application(mysqlUrl, mongoUrl)

        self.context = Context(self.app)
    
    def test_getsample(self):
        req = GetCaseListRequest(
            tags=['hard']
        )
        result, statData = self.context.getSampleApplication(AUDIT_TYPE_HOSPITAL).getSampleCase(
            req, limit=5, sampleNum=5
        )
        for item in result:
            print(item.caseId, item.tags)
        print(statData)
        assert(len(result) > 0)
    
    def test_submit(self):
        app = self.context.getSampleApplication(AUDIT_TYPE_HOSPITAL)
        record = app.submitSampleResult(
            ['7948886', '7948887', '7948897'],
            '大数ai', '大数ai'
        )
        print(record.id)
        result = app.getSampleRecordHistory(req=GetSampleRecordRequest(
            id=record.id
        ))
        print([item.id for item in result])
        assert(len(result) == 1)

        app.assignExpert(
            record.id, SampleRecord.ASSIGN_TYPE_AVG
        )
        # 获取明细记录, 应该为3
        req = GetCaseListRequest(
            sampleRecordId=record.id
        )        
        result = list(self.context.getCaseApplication(AUDIT_TYPE_HOSPITAL).getCaseList(req))
        assert(len(result) == 3)
        # 检查对应的专家已经分配
        for item in result:
            assert(item.sampleRecordItem.expertId is not None)

        # 恢复现场,删除数据
        app.removeSampleRecord(record.id)
        # 再次获取sample_record, 应该获取不到了
        result = app.getSampleRecordHistory(req=GetSampleRecordRequest(
            id=record.id
        ))
        assert(len(result) == 0)
        # 再次获取明细记录, 应该为0
        req = GetCaseListRequest(
            sampleRecordId=record.id
        )        
        result = list(self.context.getCaseApplication(AUDIT_TYPE_HOSPITAL).getCaseList(req))
        assert(len(result) == 0)
        




