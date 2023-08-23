#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:28:05

'''
import logging
from typing import Iterable, List

import arrow
from sqlalchemy import and_

from qcaudit.common.const import AUDIT_TYPE_ACTIVE
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.repobase import RepositoryBase


class AuditRecordRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.auditModel = AuditRecord.getModel(app)
        self.caseModel = app.mysqlConnection["case"]

    def getByCaseId(self, session, caseId: str) -> List[AuditRecord]:
        """获取所有历史记录

        Args:
            caseId (str):
        """
        records = []
        query = session.query(self.auditModel).join(
            self.caseModel, and_(self.auditModel.caseId == self.caseModel.caseId,
                                 self.auditModel.id == self.caseModel.audit_id)).filter(
            self.auditModel.caseId == caseId)
        for row in query.all():
            records.append(AuditRecord(row))
        return records

    def getListByCaseId(self, session, caseId: str) -> List[AuditRecord]:
        """获取所有历史记录

        Args:
            caseId (str):
        """
        records = []
        for row in session.query(self.auditModel).filter(self.auditModel.caseId == caseId).all():
            records.append(AuditRecord(row))
        return records

    def get(self, session, id) -> AuditRecord:
        """获取一个记录

        Args:
            session ([type]): [description]
            id ([type]): [description]
        """
        row = session.query(self.auditModel).filter_by(
            id=id
        ).first()
        if row:
            return AuditRecord(row)
        return None
    
    def add(self, session, item: AuditRecord):
        """增加一条记录

        Args:
            session ([type]): [description]
            item (AuditRecord): [description]
        """
        session.add(item.model)

    def calculateFirstpageProblemCount(self, session, auditId: int):
        """计算首页问题数量

        Args:
            auditId (int): [description]
        """
        raise NotImplementedError()
    
    def getReviewers(self, session, kword='', isFinal=False) -> List[str]:
        """获取所有审核人列表, 此列表基于统计, 需要缓存

        Args:
            session ([type]): [description]
            kword (str, optional): [description]. Defaults to ''.
            isFinal (bool, optional): [description]. Defaults to False.

        Returns:
            List[str]: [description]
        """
        if self.auditType == AUDIT_TYPE_ACTIVE:
            active_record = self.app.mysqlConnection["active_record"]
            query = session.query(active_record.operator_name).distinct()
            return [item.operator_name for item in query.all()]
        field = AuditRecord.getOperatorFields(
            self.auditType,
            isFinal=False
        )
        reviewers = set()
        query = session.query(getattr(self.auditModel, field.reviewerNameField)).distinct()
        for row in query:
            if not row[0]:
                continue
            if not kword or kword in row[0]:
                reviewers.add(row[0])
        field1 = AuditRecord.getOperatorFields(
            self.auditType,
            isFinal=True
        )
        query1 = session.query(getattr(self.auditModel, field1.reviewerNameField)).distinct()
        for row in query1:
            if not row[0]:
                continue
            if not kword or kword in row[0]:
                reviewers.add(row[0])
        return list(reviewers)

    def getAuditRecordPeriods(self, session, caseId):
        """根据caseId获取申请记录
        按照申请时间分成一段一段的申请记录覆盖范围
        """
        # 根据audit_record 记录的每次申请归档时间，计算每次申请记录涵盖的时间段范围
        periods = []
        last_apply_time = arrow.get("2000-01-01")
        for audit in self.getListByCaseId(session, caseId):
            try:
                if audit.applyTime:
                    apply_time = arrow.get(audit.applyTime)
                    if apply_time < last_apply_time:
                        continue
                    periods.append((audit, last_apply_time, apply_time))
                    last_apply_time = apply_time
            except Exception as e:
                logging.exception(e)
                continue
        return periods
