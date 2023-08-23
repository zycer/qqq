#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 22:59:41

'''
import json
import logging
from typing import Iterator, List, Optional
from qcaudit.app import Application
from qcaudit.domain.case.case import CaseDoctor
from qcaudit.domain.case.emr import EmrContent, EmrDocument
from qcaudit.domain.case.req import GetEmrListRequest
from qcaudit.domain.repobase import RepositoryBase
from datetime import datetime
from qcaudit.utils.htmldiffer import diff
from sqlalchemy import func, distinct, and_
from qcaudit.domain.case.emrversion import EmrVersion
from bs4 import BeautifulSoup


class EmrRepository(RepositoryBase):

    def __init__(self, app: Application, auditType: str):
        super().__init__(app, auditType)
        self.emrInfoModel = app.mysqlConnection['emrInfo']
        self.emrContentModel = app.mysqlConnection['emrContent']

    def getEmrList(self, session, req: GetEmrListRequest) -> Iterator[EmrDocument]:
        """获取文书列表

        Args:
            session ([type]): [description]
            req (GetEmrListRequest): [description]

        Returns:
            List[EmrDocument]: [description]
        """
        if req.withContent:
            query = session.query(self.emrInfoModel, self.emrContentModel).join(
                self.emrContentModel, and_(self.emrInfoModel.caseId == self.emrContentModel.caseId,
                                           self.emrInfoModel.docId == self.emrContentModel.docId), isouter=True
            ).order_by(self.emrInfoModel.createTime)
        else:
            query = session.query(self.emrInfoModel).order_by(self.emrInfoModel.recordTime)
        query = req.apply(query, self.app.mysqlConnection)
        result = []
        for row in query.all():
            if req.withContent:
                result.append(EmrDocument(row[0], row[1]))
            else:
                result.append(EmrDocument(row))
        return result

    def count(self, session, req: GetEmrListRequest) -> int:
        query = session.query(self.emrInfoModel)
        query = req.apply(query, self.app.mysqlConnection)
        return query.count()

    def getEmrListByCaseId(self, session, caseId: str, withContent=False):
        """根据caseId获取文书列表

        Args:
            session ([type]): [description]
            withContent (bool, optional): [description]. Defaults to False.
        """
        req = GetEmrListRequest(
            size=10000,
            caseId=caseId,
            withContent=withContent
        )
        return self.getEmrList(session, req)

    def getEmrVersions(self, session, caseId: str, docId: str) -> Iterator[EmrDocument]:
        """获取文书版本

        """
        model = self.app.mysqlConnection['auditEmrInfo']
        audit_model = self.app.mysqlConnection['audit_record']
        versions = []
        audit_records = session.query(audit_model).filter(audit_model.caseId==caseId).all()
        old_audit = audit_records[0]
        old_dict = {}
        for obj in audit_records[1:]:
            if obj.id == old_audit.id:
                continue
            else:
                old_dict[obj] = old_audit.id
                old_audit = obj
        for item in old_dict:
            audit_emr_obj=session.query(model).filter(model.caseId==caseId,model.docId==docId,model.auditId==old_dict[item]).order_by(model.createTime.desc()).first()
            if not audit_emr_obj:
                continue
            versions.append(EmrVersion(audit_emr_obj, item))
        return versions

    def getLastVersionBefore(self, session, caseId, docId: str, endTime: datetime) -> EmrDocument:
        """获取指定时间前的最后一个版本

        Args:
            session ([type]): [description]
            caseId ([type]): [description]
            docId (str): [description]
            endTime (datetime): [description]
        """
        info = session.query(self.emrInfoModel).filter_by(
            caseId=caseId,
            docId=docId
        ).first()
        if not info:
            raise ValueError(f'cannot found emrinfo {caseId} {docId}')
        row = session.query(self.emrContentModel).filter_by(
            caseId=caseId,
            docId=docId
        ).filter(self.emrContentModel.updateTime < endTime).order_by(
            self.emrContentModel.updateTime.desc()
        ).first()
        return EmrDocument(info, row)

    def getEmrVersionByAudit(self, session, caseId: str, docId: str, auditObj) -> EmrDocument:
        """获取指定auditId对应的版本

        Args:
            session ([type]): [description]
            caseId (str): [description]
            docId (str): [description]
            auditId (int): [description]
        """
        model = self.app.mysqlConnection['auditEmrInfo']
        row = session.query(model).filter_by(caseId=caseId, docId=docId).filter(model.createTime < auditObj.applyTime).order_by(model.createTime.desc()).first()
        if not row:
            return None
        version = row.dataId
        content = session.query(self.emrContentModel).filter_by(id=version).first()
        if not content:
            logging.error(f'cannot find emrContent of {version} {docId} {caseId}')
            return None
        info = session.query(self.emrInfoModel).filter_by(
            caseId=caseId,
            docId=docId
        ).first()
        return EmrDocument(info, content)

    def diff(self, old: EmrDocument, new: EmrDocument) -> str:
        """历史版本和最新版本文书内容做diff
        """
        if not old or not new:
            return ""
        style = "<style type=\"text/css\">span.diff_delete {text-decoration: line-through;color: #989898;} span.diff_insert {color: #1890FF;}</style>"
        old_html = BeautifulSoup(old.getEmrHtml(), 'lxml')
        new_html = BeautifulSoup(new.getEmrHtml(), 'lxml')
        # todo 可以把模板里的无用字符去掉，比如 标签里的 did token comment id

        return style + diff.HTMLDiffer(str(old_html), str(new_html)).combined_diff

    def get(self, session, caseId: str, docId: str, withContent=False) -> Optional[EmrDocument]:
        doc = session.query(self.emrInfoModel).filter_by(
            caseId=caseId,
            docId=docId
        ).first()
        if not doc:
            return None
        content = None
        if withContent:
            content = session.query(self.emrContentModel).filter_by(
                id=doc.emrContentId
            ).first()
        return EmrDocument(doc, content)

    def getEmrContentNum(self, session, caseId):
        """
        根据emr id列表获取对应content数量以及ID
        """
        res = dict()
        record_model = self.app.mysqlConnection['auditEmrInfo']
        record_num = session.query(record_model.auditId).filter(record_model.auditId != None,record_model.caseId == caseId).distinct().count()
        if record_num < 2:
            return res
        contents = session.query(self.emrContentModel).filter(self.emrContentModel.caseId == caseId).all()
        for item in contents:
            if item.docId not in res:
                res[item.docId] = 1
                continue
            res[item.docId] += 1

        return res

    def getAuditEmrLog(self, session, caseId):
        """
        根据caseId查询文书的修改历史记录
        """
        return session.query(self.app.mysqlConnection['auditEmrInfo']).filter_by(caseId=caseId).all()

    def catalogEmr(self, emrList, documents, order=None):
        """
        将文书列表归类
        """
        catalog = []
        index = {}
        if not order:
            order = {document.name: document.type_order for document in documents}

        # 病程记录目录，将未识别的查房记录加入到此目录
        hos_course_order = 10000
        for document in documents:
            if document.type_name == '病程记录':
                hos_course_order = document.type_order
                break

        type_orders = [v for k, v in order.items()]
        type_orders.sort()

        for orderId in type_orders:
            if orderId in index:
                continue
            else:
                catalog.append({
                    'id': orderId,
                    'items': []
                })
                index[orderId] = len(catalog) - 1

        for emr in emrList:
            # 忽略缺失文书
            if emr.docId == '0':
                continue
            # 文书按documents中设置排序
            orderId = order.get(emr.getSimpleDocumentName(), 10000)

            # 未识别的查房记录加到病程记录目录中
            if orderId == 10000 and '查房记录' in emr.documentName:
                orderId = hos_course_order
                order[emr.getSimpleDocumentName()] = hos_course_order
            if orderId == 10000 and '日常病程记录' in emr.documentName:
                orderId = hos_course_order
                order[emr.getSimpleDocumentName()] = hos_course_order

            if orderId in index:
                catalog[index[orderId]]['items'].append(emr.docId)
            else:
                catalog.append({
                    'id': orderId,
                    'items': [emr.docId]
                })
                index[orderId] = len(catalog) - 1
        return catalog

    def getDocIdList(self, session, caseId):
        result = list()
        query = session.query(distinct(self.emrInfoModel.docId)).filter(self.emrInfoModel.caseId == caseId)
        for item in query.all():
            result.append(item[0])
        return result

    def getParserResult(self, session, caseId):
        result = dict()
        model = self.app.mysqlConnection['emrParserResult']
        query = session.query(model.docId, model.field).filter(model.caseId == caseId)
        for item in query.all():
            if (docId := item.docId) not in result:
                result[docId] = [json.loads(item.field)]
            else:
                result[docId].append(json.loads(item.field))
        return result
