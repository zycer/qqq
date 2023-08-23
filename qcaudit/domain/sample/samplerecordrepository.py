#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 13:42:10

'''

from datetime import datetime
from typing import Iterable, Union, List

from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.req import ListRequestBase
from qcaudit.domain.sample.req import GetSampleRecordRequest, GetSampleDetailRequest
from qcaudit.domain.sample.sampleoperation import SampleOperation
from qcaudit.domain.sample.samplerecord import SampleRecord
from qcaudit.domain.sample.samplerecorditem import SampleRecordItem

import arrow


class SampleRecordRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.recordModel = SampleRecord.getModel(app)
        self.itemModel = SampleRecordItem.getModel(app)
        self.operationModel = SampleOperation.getModel(app)
        self.caseModel = self.app.mysqlConnection['case']
        self.auditRecordModel = self.app.mysqlConnection['audit_record']
    
    def getList(self, session, req: GetSampleRecordRequest):
        """获取抽取历史列表

        Args:
            session ([type]): [description]
            req ([GetSampleRecordRequest]): [description]

        Raises:
            NotImplementedError: [description]
        """
        query = session.query(self.recordModel)
        query = req.apply(query, self.app.mysqlConnection)
        result = []
        for row in query.all():
            result.append(SampleRecord(row))

        return result

    def getById(self, session, sampleId):
        sample = session.query(self.recordModel).filter_by(id=sampleId).first()
        if sample:
            return SampleRecord(sample)
        return None

    def getCount(self, session, req: GetSampleRecordRequest) -> int:
        """ 获取抽取总数
        """
        query = session.query(self.recordModel)
        query = req.applyFilter(query, self.app.mysqlConnection)
        
        return query.count()
    
    def delete(self, session, recordId: int):
        """删除一条记录

        Args:
            session ([type]): [description]
            recordId (int): [description]
        """
        session.query(self.recordModel).filter_by(
            id=recordId
        ).delete()
        session.query(self.itemModel).filter_by(
            recordId=recordId
        ).delete()
    
    def deleteItem(self, session, itemId: int):
        """删除一条明细记录

        Args:
            session ([type]): [description]
            itemId (int): [description]
        """
        session.query(self.itemModel).filter_by(
            id=itemId
        ).delete()

    def add(self, session, obj: SampleRecord):
        """创建一条记录
        """
        session.add(obj.model)
    
    def addItem(self, session, obj: SampleRecordItem):
        """创建一条item记录
        """
        session.add(obj.model)

    def addOperation(self, session, obj: SampleOperation):
        """创建一条操作日志
        """
        session.add(obj.model)

    def getRecordById(self, session, id):
        """获取一条记录

        Args:
            id ([type]): [description]
        """
        row = session.query(self.recordModel).filter_by(
            id=id
        ).first()
        return SampleRecord(row)
    
    def getItemList(self, session, recordId: int, auditType: str = "") -> List[SampleRecordItem]:
        """获取抽取的病历列表, 搜索接口通过CaseApplication提供的接口实现, 这里只根据id获取

        Args:
            session ([type]): 
            recordId (int): 
            auditType (str):

        Returns:
            List[SampleRecordItem]: [description]
        """
        query = self.getItemQuery(session)
        query = query.join(self.auditRecordModel, self.auditRecordModel.id == self.caseModel.audit_id)
        # 平均分配时保证只分配状态为1/5
        approved_status = [AuditRecord.STATUS_PENDING, AuditRecord.STATUS_APPLIED]
        query = query.filter(self.itemModel.recordId == recordId,
                             getattr(self.auditRecordModel,
                                     AuditRecord.getOperatorFields(auditType).statusField).in_(approved_status))
        result = []
        for row in query.all():
            result.append(SampleRecordItem(row[1], row[0]))
            
        return result
    
    def getItemQuery(self, session):
        query = session.query(self.caseModel, self.itemModel).join(
            self.itemModel, self.caseModel.caseId == self.itemModel.caseId,
            isouter=True
        )
        return query

    def getItemCount(self, session, req: GetSampleDetailRequest) -> int:
        """ 获取抽取病历总数
        """
        query = session.query(self.itemModel, self.caseModel, self.auditRecordModel).join(
            self.itemModel, self.caseModel.caseId == self.itemModel.caseId, isouter=True).join(
                self.auditRecordModel, self.caseModel.audit_id == self.auditRecordModel.id, isouter=True)
        query = req.applyFilter(query, self.app.mysqlConnection)
        return query.count()

    def getItemListByQuery(self, session, req: GetSampleDetailRequest):
        """ 获取抽取病历列表

        Args:
            session ([type]): [description]
            req ([type]): [description]

        Raises:
            NotImplementedError: [description]
        """
        
        query = session.query(self.itemModel, self.caseModel, self.auditRecordModel).join(
            self.itemModel, self.caseModel.caseId==self.itemModel.caseId,
            isouter=True).join(
            self.auditRecordModel, self.caseModel.audit_id == self.auditRecordModel.id, isouter=True
        )
        query = req.apply(query, self.app.mysqlConnection, isSort=0)
        result = []
        for item, case, auditRecord in query.all():
            result.append(SampleRecordItem(item, case, auditRecord))
        return result

    def getItemById(self, session, itemId, many=0):
        """获取一条item记录

        Args:
            session ([type]): [description]
            itemId ([type]): [description]
        """
        query = self.getItemQuery(session)
        if many:
            model = self.itemModel
            row = query.filter(model.id.in_(itemId)).all()
        else:
            row = query.filter_by(id=itemId).first()
        if not row:
            return None
        return SampleRecordItem(row[1], row[0]) if not many else [SampleRecordItem(r[1], r[0]) for r in row]
    
    def getItemByCaseId(self, session, auditType, caseId):
        """获取一条item记录

        """
        query = self.getItemQuery(session)
        row = query.filter_by(auditType=auditType, caseId=caseId).first()
        if not row:
            return None
        return SampleRecordItem(row[1], row[0])

    def getAssignedDoctors(self, session, keyWord):
        reviewers = set()
        query = session.query(self.itemModel.expertName).distinct()
        for row in query:
            if not row[0]:
                continue
            if not keyWord or keyWord in row[0]:
                reviewers.add(row[0])
        return list(reviewers)

    def getSampleOperations(self, session, sampleId):
        result = []
        for row in session.query(self.operationModel).filter_by(sample_id=sampleId).all():
            result.append(SampleOperation(row))
        return result

    def getSampleOperationById(self, session, operationId):
        operation = session.query(self.operationModel).filter_by(id=operationId).first()
        if operation:
            return SampleOperation(operation)
        return None
