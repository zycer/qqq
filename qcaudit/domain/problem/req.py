#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-11 13:43:00

'''


from dataclasses import dataclass

from sqlalchemy import or_

from qcaudit.domain.req import ListRequestBase


@dataclass
class GetProblemListRequest(ListRequestBase):

    id: int = 0
    caseId: str = ''
    docId: str = ''
    auditId: int = 0
    qcItemId: int = 0
    auditType: str = ''
    # 是否包含已删除的问题
    withDeleted: bool = False
    # 默认情况下获取全部问题
    size: int = 10000
    ignoreAi: bool = False
    isAddRefuse: int = 0  # 是否为追加退回查询问题列表 0-否 1-是
    nowStatusFlag: int = 0  # 是否为病历现状页面查询问题列表 0-否 1-是
    caseStatus: int = 0  # 病历状态 1-待质控 3-已归档 4-已驳回 5-待提交
    refuseCount: int = 0  # 病历驳回次数

    def applyFilter(self, query, connection):
        problemModel = connection['caseProblem']
        qcItemModel = connection['qcItem']
        # 指定id忽略其他条件
        if self.id:
            query = query.filter(
                problemModel.id==self.id
            )
            return query

        if self.caseId:
            query = query.filter(
                problemModel.caseId==self.caseId
            )
        if self.docId:
            query = query.filter(
                problemModel.docId==self.docId
            )
        if self.auditId:
            query = query.filter(
                problemModel.audit_id==self.auditId
            )
        if self.qcItemId:
            query = query.filter(
                problemModel.qcItemId==self.qcItemId
            )
        if not self.withDeleted:
            query = query.filter(
                problemModel.is_deleted==0
            )
        if self.ignoreAi:
            query = query.filter(
                problemModel.from_ai==0
            )
        if self.nowStatusFlag:
            # 病历现状页, 根据病历状态不同展示不同问题
            if self.caseStatus == 5:
                # 待提交
                query = query.filter(problemModel.auditType == "active")
            elif self.caseStatus == 1:
                # 质控中, 需判断是否有过驳回记录
                if self.refuseCount:
                    # 存在驳回记录只展示驳回过的问题
                    query = query.filter(problemModel.refuseFlag == 1)
                else:
                    # 不存在驳回记录只展示事中问题
                    query = query.filter(problemModel.auditType == "active")
            elif self.caseStatus == 4:
                # 已退回
                query = query.filter(problemModel.refuseFlag == 1)
            elif self.caseStatus == 3:
                # 已归档
                query = query.filter(1 != 1)
            return query
        if self.isAddRefuse:
            query = query.filter(problemModel.refuseFlag == 0)
        if self.auditType:
            query = query.filter(
                problemModel.auditType==self.auditType
            )
        # 根据质控点将提示问题放在后面
        query = query.order_by(qcItemModel.enableType.asc())
        return query

