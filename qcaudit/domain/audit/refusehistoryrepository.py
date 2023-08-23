#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:29:57

'''

from typing import Iterable, Optional, List

import arrow

from qcaudit.domain.audit.refusehistory import RefuseHistory
from qcaudit.domain.audit.refusedetail import RefuseDetail
from qcaudit.domain.repobase import RepositoryBase


class RefuseHistoryRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.model = RefuseHistory.getModel(self.app)

    def add(self, session, item: RefuseHistory):
        """添加一条驳回历史

        Args:
            item (RefuseHistory): [description]
        """
        session.add(item.model)

    def getByAuditId(self, session, auditId: int) -> Optional[RefuseHistory]:
        """根据auditId获取驳回的问题, 只返回最后一条
           v2版本要根据refuse_time获取, 由于一个audit_id只会获取一个, 所以取最后一次即可
        Args:
            auditId (str): [description]
        """
        row = session.query(self.model).filter(
            self.model.audit_id == auditId
        ).order_by(self.model.refuse_time.desc()).first()
        if not row:
            return None
        return RefuseHistory(row)

    def getRefuseHistory(self, session, caseId: str, refuseTime: str):
        """驳回记录
        """
        result = []
        row = session.query(self.model).filter_by(caseId=caseId, refuse_time=refuseTime).first()
        if not row:
            return None
        return RefuseDetail(row)

    def getRefuseDetail(self, session, caseId: str, historyId: int) -> List[RefuseDetail]:
        """

        Args:
            session ([type]): [description]
            caseId (str): [description]
            historyId (int): [description]
        """
        model = RefuseDetail.getModel(self.app)
        result = []
        for row in session.query(model).filter_by(caseId=caseId, history_id=historyId):
            result.append(RefuseDetail(row))
        return result

    def getByCaseId(self, session, caseId, auditType) -> Optional[RefuseHistory]:
        """根据caseId获取驳回的问题, 只返回最后一条
        """
        row = session.query(self.model).filter(
            self.model.caseId == caseId,
            self.model.auditType == auditType
        ).order_by(self.model.refuse_time.desc()).first()
        if not row:
            return None
        return RefuseHistory(row)

    def getALlByCaseId(self, session, caseId, auditType):
        """
        根据caseId获取全部驳回记录
        :return:
        """
        data = session.query(self.model).filter(
            self.model.caseId == caseId, self.model.auditType == auditType).all()
        rh_list = []
        for row in data:
            rh_list.append(RefuseHistory(row))
        return rh_list

    def revokeRefuse(self, session, caseId, auditId):
        """
        删除驳回记录
        """
        timestamp = arrow.utcnow().to('+08:00').naive
        # 删除驳回详情
        detailModel = RefuseDetail.getModel(self.app)
        session.query(detailModel).filter_by(caseId=caseId, audit_id=auditId, is_deleted=0).update({"is_deleted": 1})
        # 删除驳回主记录
        session.query(self.model).filter_by(audit_id=auditId, revoke_flag=0).update({
            "revoke_flag": 1,
            "revoke_time": timestamp
        })
