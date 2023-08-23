#!/usr/bin/env python3
import json
from typing import List

import arrow

from qcaudit.app import Application
from qcaudit.domain.dict.qcitem import QcItem
from qcaudit.domain.qcgroup.qcitem_req import GetItemsListRequest
from qcaudit.domain.repobase import RepositoryBase


class QcItemRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = QcItem.getModel(app)

    def getList(self, session, req: GetItemsListRequest) -> List[QcItem]:
        """获取质控项列表
        """
        qcItem_rule_model = self.app.mysqlConnection["qcItem_rule"]
        model = QcItem.getModel(self.app)
        query = session.query(model, qcItem_rule_model).join(qcItem_rule_model, model.id == qcItem_rule_model.qcItemId, isouter=True)
        query = req.apply(query, self.app.mysqlConnection)
        result = []
        data = query.all()
        for row, rule in data:
            result.append(QcItem(row, rule=rule))
        return result

    def count(self, session, req: GetItemsListRequest):
        model = QcItem.getModel(self.app)
        query = session.query(model)
        query = req.applyFilter(query, self.app.mysqlConnection)
        return query.count()

    def add(self, session, qcItem: QcItem):
        """添加质控点
        """
        session.add(qcItem.model)

    def deleteItems(self, session, items: List[int]):
        """删除质控点
        items: qcItemId 质控点id
        """
        model = QcItem.getModel(self.app)
        session.query(model).filter(model.id.in_(items)).update({'is_deleted': 1}, synchronize_session=False)

    def enableItem(self, session, itemId, enableStatus, enableType):
        """启用质控点
        """
        model = QcItem.getModel(self.app)
        if enableStatus:
            session.query(model).filter(model.id == itemId).update({'enable': enableStatus}, synchronize_session=False)
        if enableType:
            session.query(model).filter(model.id == itemId).update({'enableType': enableType}, synchronize_session=False)

    def approveItem(self, session, itemId):
        """确认质控点
        """
        model = QcItem.getModel(self.app)
        session.query(model).filter(model.id == itemId).update({'approve_status': 2}, synchronize_session=False)

    def updateRule(self, session, qcItemId, data):
        """
        更新质控点规则
        :return:
        """
        qcItem_rule_model = self.app.mysqlConnection["qcItem_rule"]
        session.query(qcItem_rule_model).filter(qcItem_rule_model.qcItemId == qcItemId).update(data, synchronize_session=False)

    def sendReload(self):
        """
        发送消息至ruleengine重新加载规则
        :return:
        """
        self.app.mq.publish({"message": "reload"}, routing_key="qcItem.rule.reload")

    def queryCodeIsExist(self, code):
        """
        判断质控点code是否存在
        :param code:
        :return:
        """
        if not code:
            return True
        qcItem_model = self.app.mysqlConnection["qcItem"]
        with self.app.mysqlConnection.session() as session:
            if session.query(qcItem_model.id).filter(qcItem_model.code == code).first():
                return False
            return True

    def getQcItemByIds(self, session, ids):
        items = session.query(self.model).filter(self.model.id.in_(ids)).all()
        return items

    def getDiseaseName(self, disease):
        """
        根据诊断编码获取诊断名称
        :return:
        """
        diag = self.app.mysqlConnection["diagnosis_dict"]
        with self.app.mysqlConnection.session() as session:
            query = session.query(diag).filter(diag.code == disease)
            diag_info = query.first()
            if diag_info:
                return diag_info.name or ""
        return ""
