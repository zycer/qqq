#!/usr/bin/env python3
"""
  规则组
"""

from typing import Iterable, List
from qcaudit.domain.qcgroup.qcgroup import QcGroup, QcCategory, QcCateItems
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, \
    AUDIT_TYPE_ACTIVE
import logging


class QcGroupRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.qcGroupModel = QcGroup.getModel(app)
        self.qcCategoryModel = self.app.mysqlConnection['qcCategory']
        self.qcCateItemsModel = self.app.mysqlConnection['qcCateItems']

    def getGroupId(self):
        # TODO 修改成根据配置返回
        return {
            AUDIT_TYPE_DEPARTMENT: 1,
            AUDIT_TYPE_HOSPITAL: 2,
            AUDIT_TYPE_FIRSTPAGE: 3,
            AUDIT_TYPE_EXPERT: 4,
            AUDIT_TYPE_ACTIVE: 5,
        }.get(self.auditType)

    def getQcGroup(self, session, groupId=0):
        """查询质控规则组规则

        Args:
            session ([type]): [description]
            groupId ([int]): [规则组id]
        """
        if not groupId:
            groupId = self.getGroupId()
        group = session.query(self.qcGroupModel).filter_by(id=groupId).first()
        if not group:
            return None
        return QcGroup(group, self.getQcCategory(session, groupId), self.getQcCateItems(session, groupId))

    def getQcCategory(self, session, groupId=0, sug='', cid=0):
        """规则组-类别
        """
        if not groupId:
            groupId = self.getGroupId()
        categories = []
        if cid:
            row = session.query(self.qcCategoryModel).filter_by(id=cid).first()
            if not row:
                return categories
            categories.append(row)
        else:
            query = session.query(self.qcCategoryModel).filter_by(groupId=groupId, is_deleted=0)
            if sug:
                query = query.filter(self.qcCategoryModel.name.like('%%%s%%' % sug))
            for row in query.order_by(self.qcCategoryModel.parentId).order_by(self.qcCategoryModel.id):
                categories.append(QcCategory(row))
        return categories

    def getQcCateItems(self, session, groupId=0, withItem=False, qci=0):
        """规则组-规则项
        """
        if not groupId:
            groupId = self.getGroupId()
        qcItemModel = self.app.mysqlConnection['qcItem']
        items = []
        if qci:
            row = session.query(self.qcCateItemsModel).filter_by(id=qci).first()
            if not row:
                return items
            items.append(row)
            return items
        if withItem:
            for row, item in session.query(self.qcCateItemsModel, qcItemModel).join(
                    qcItemModel, self.qcCateItemsModel.itemId == qcItemModel.id, isouter=True
            ).filter(self.qcCateItemsModel.groupId == groupId):
                items.append(QcCateItems(row, item))
            return items
        for row in session.query(self.qcCateItemsModel).filter_by(groupId=groupId):
            items.append(QcCateItems(row))
        return items

    def getQcItemsStandardName(self, session):
        """
        过滤不存在的文书 查询全部文书名
        :param session:
        :return:
        """
        qcItemModel = self.app.mysqlConnection['qcItem']
        names = []
        for row in session.query(qcItemModel.standard_emr).group_by(qcItemModel.standard_emr):
            if row.standard_emr and str(row.standard_emr) not in ("0", " "):
                names.append(row.standard_emr)
        return names

    def deleteQcCateItemsById(self, session, idList=None):
        if idList:
            session.query(self.qcCateItemsModel).filter(self.qcCateItemsModel.id.in_(idList)).delete(synchronize_session=False)
        return True

    def deleteQcCateItemsByItem(self, session, itemsList=None):
        if itemsList:
            session.query(self.qcCateItemsModel).filter(self.qcCateItemsModel.itemId.in_(itemsList)).delete(synchronize_session=False)
        return True

    def addQcCateItems(self, session, qcCateItem: QcCateItems):
        """新增规则组项
        """
        session.add(qcCateItem.model)

    def getGroups(self, session, sug=''):
        """规则组列表
        """
        groups = []
        query = session.query(self.qcGroupModel)
        if sug:
            query = query.filter(self.qcGroupModel.name.like('%%%s%%' % sug))
        for group in query.all():
            if not group:
                return None
            groups.append(QcGroup(group, self.getQcCategory(session, group.id), self.getQcCateItems(session, group.id)))
        return groups

    def getFirstCategoryId(self, session):
        """第一个质控类别分组的id
        """
        categories = self.getQcCategory(session, self.getGroupId())
        if categories:
            return categories[0].id
        return 0
