#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 18:09:40

'''
import copy
import json
import logging
from collections import defaultdict
from datetime import datetime
import pandas as pd
from typing import Iterator, List, Optional

import arrow
from qc_document_classifier.contrast import DocTypeItem
from qc_document_classifier.special import SpecialRaw
from sqlalchemy import or_, text

from qcaudit.application.applicationbase import ApplicationBase
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, \
    AUDIT_TYPE_ACTIVE, CASE_STATUS_ARCHIVED, EMR_DOCUMENTS_REG, EXPORT_FILE_AUDIT_TYPE
from qcaudit.common.result import CommonResult
from qcaudit.config import Config
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.audit.auditrecordrepository import AuditRecordRepository
from qcaudit.domain.case.case import Case, CaseDoctor
from qcaudit.domain.case.caserepository import CaseRepository
from qcaudit.domain.case.emr import EmrDocument
from qcaudit.domain.case.emrrepository import EmrRepository
from qcaudit.domain.case.orderrepository import OrderRepository
from qcaudit.domain.case.assayrepository import AssayRepository
from qcaudit.domain.case.examrepository import ExamRepository
from qcaudit.domain.case.req import ExportCaseListRequest, GetCaseListRequest, GetEmrListRequest, GetOrderListRequest, \
    GetAssayListRequest, GetExamListRequest
from qcaudit.domain.case.emrsvc import EmrService
from qcaudit.domain.dict import DoctorRepository, CaseTagRepository, DocumentsRepository, QcItemRepository
from qcaudit.domain.dict.external_link_repository import ExternalLinkRepository
from qcaudit.domain.lab.labrepository import LabRepository
from qcaudit.domain.lab.req import GetLabListRequest
from qcaudit.domain.message import MessageRepo
from qcaudit.domain.problem.problem import Problem
from qcaudit.domain.problem.problemrepository import ProblemRepository
from qcaudit.domain.problem.req import GetProblemListRequest
from qcaudit.domain.problem.statsreq import GetProblemStatsRequest
from qcaudit.domain.qcgroup.qcitem_req import GetItemsListRequest
from qcaudit.domain.report.score_report_repository import ScoreReportRepository
from qcaudit.domain.sample.samplerecorditem import SampleRecordItem
from qcaudit.service.protomarshaler import parseStatusName, parseRating, getActiveProblemStatus
from qcaudit.utils.document_classifier.classifier import Classifier
from qcaudit.utils.towebconfig import *
from redis import Redis


class CaseApplication(ApplicationBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self._caseRepository = None
        self._emrRepository = None
        self._orderRepository = None
        self._auditRepository = None
        self._problemRepository = None
        self._doctorRepository = None
        self._caseTagRepository = None
        self._documentsRepository = None
        self._qcItemRepository = None
        self._scoreReportRepository = None
        self._emrSvc = None
        self._assayRepository = None
        self._examRepository = None
        self._labRepository = None
        self._emrClassifier = None
        self._externalLinkRepo = None
        self.initCaseRepository()
        self.initEmrRepository()
        self.initAuditRepository()
        self.initOrderRepository()
        self.initProblemRepository()
        self.initDoctorRepository()
        self.initCaseTagRepository()
        self.initDocumentsRepository()
        self.initQcItemRepository()
        self.initAssayRepository()
        self.initExamRepository()
        self.initLabRepository()
        self.initScoreReportRepository()
        self.initEmrClassifier()
        self.initExternalLinkRepository()
        self._messageRepository = MessageRepo(app, auditType)

    def initCaseRepository(self):
        if not self._caseRepository:
            self._caseRepository = CaseRepository(self.app, self.auditType)

    def initOrderRepository(self):
        if not self._orderRepository:
            self._orderRepository = OrderRepository(self.app, self.auditType)

    def initEmrRepository(self):
        if not self._emrRepository:
            self._emrRepository = EmrRepository(self.app, self.auditType)

    def initAuditRepository(self):
        if not self._auditRepository:
            self._auditRepository = AuditRecordRepository(self.app, self.auditType)

    def initProblemRepository(self):
        if not self._problemRepository:
            self._problemRepository = ProblemRepository(self.app, self.auditType)

    def initDoctorRepository(self):
        if not self._doctorRepository:
            self._doctorRepository = DoctorRepository(self.app, self.auditType)

    def initCaseTagRepository(self):
        if not self._caseTagRepository:
            self._caseTagRepository = CaseTagRepository(self.app, self.auditType)

    def initDocumentsRepository(self):
        if not self._documentsRepository:
            self._documentsRepository = DocumentsRepository(self.app, self.auditType)

    def initQcItemRepository(self):
        if not self._qcItemRepository:
            self._qcItemRepository = QcItemRepository(self.app, self.auditType)

    def initScoreReportRepository(self):
        if not self._scoreReportRepository:
            self._scoreReportRepository = ScoreReportRepository(self.app, self.auditType)

    def initEmrSvc(self):
        if not self._emrSvc:
            self._emrSvc = EmrService(self.app, self.auditType)

    def initAssayRepository(self):
        if not self._assayRepository:
            self._assayRepository = AssayRepository(self.app, self.auditType)

    def initExamRepository(self):
        if not self._examRepository:
            self._examRepository = ExamRepository(self.app, self.auditType)

    def initLabRepository(self):
        if not self._labRepository:
            self._labRepository = LabRepository(self.app, self.auditType)

    def initEmrClassifier(self):
        """标准文书对照分类器"""
        if not self._emrClassifier:
            # 所有标准文书集合
            standard_types = [item[0] for item in EMR_DOCUMENTS_REG]
            # 标准文书正则规则
            doc_type_items = [DocTypeItem.parse_obj({'name': item[0], 'type': item[1], 'reg': item[2]}) for item in EMR_DOCUMENTS_REG]
            # 由医学部人工确认过的对照表
            mapping_data = []
            with self.app.mysqlConnection.session() as session:
                for d in self._documentsRepository.getList(session):
                    if d.standard_name not in standard_types:
                        continue
                    mapping_data.append((d.name, d.standard_name))
            # 医生职称表，用于查找副主任查房和主治查房
            doctors_data = []
            # 每个医院特有的正则表达式，可以存储在数据库表里
            regs_data = [
                ("告知(选择)(书|单)", "知情同意书"),
                ("副主任(医师|)(查|)(房|看|)", "主（副）任医师查房记录"),
                ("主治(医师|)(查|)(房|看|)", "主治医师查房记录"),
                ("手术医[师生]查[房看]", "上级医师查房记录"),
                ('术后第[1一][天日]', '术后第一天查房记录'),
                ('术后第[2二][天日]', '术后第二天查房记录'),
                ('术后第[3三][天日]', '术后第三天查房记录'),
                ('(日常|)病程记录', '病程记录'),
                ('首程', '首次病程记录'),
                ('首次病程.*', '首次病程记录'),
            ]
            # 创建实例
            special_raw = SpecialRaw(mapping=mapping_data, regs=regs_data, doctors=doctors_data)
            self._emrClassifier = Classifier(doc_type_items=doc_type_items, special_raw=special_raw)

    def initExternalLinkRepository(self):
        if not self._externalLinkRepo:
            self._externalLinkRepo = ExternalLinkRepository(self.app, self.auditType)

    def getCaseList(self, req: GetCaseListRequest):
        """获取病历列表

        Args:
            req (GetCaseListRequest): [description]

        Returns:
            List[Case]: [description]
        """
        with self.app.mysqlConnection.session() as session:
            count = self._caseRepository.count(session, req)
            result = self._caseRepository.getList(session, req)
            tags = {t.code: t for t in self.expunge(session, self._caseTagRepository.getList(session, ''))}
            if result:
                for item in result:
                    item.convertTagToModel(tags)
                    item.expunge(session)
                    # self.expunge(session, item)
            # result = list(self.expunge(session, self._caseRepository.getList(session, req)))
            return result, count

    def exportCaseList(self, req: ExportCaseListRequest):
        """导出病历列表

        Args:
            req (GetCaseListRequest): [description]
        """
        raise NotImplementedError()

    def getCaseDetail(self, caseId: str) -> Optional[Case]:
        """获取病历详情

        Args:
            caseId (str): [description]

        Returns:
            Case: [description]
        """
        with self.app.mysqlConnection.session() as session:
            row = self._caseRepository.getByCaseId(session, caseId)
            if row:
                tags = {t.code: t for t in self.expunge(session, self._caseTagRepository.getList(session, ''))}
                row.convertTagToModel(tags)
                row.expunge(session)
            return row

    def getCaseEmr(self, req: GetEmrListRequest, withNoDocOption=False) -> Iterator[EmrDocument]:
        """获取病历文书列表

        Args:
            req (GetEmrListRequest): [description]
            withNoDocOption(bool): [是否增加一项缺失文书]
        """
        emrs = []
        with self.app.mysqlConnection.session() as session:
            for emr in self.expunge(session, self._emrRepository.getEmrList(session, req)):
                emrs.append(emr)
            if withNoDocOption:
                emrs.append(EmrDocument(self._emrRepository.emrInfoModel(docId='0', documentName='缺失文书')))
        return emrs

    def getEmrCatalog(self, emrList):
        if self.app.config.get(Config.QC_DOCUMENT_CATALOG_FIELD) == "originType":
            documents = self.getDocumentsByName([emr.getOriginType() for emr in emrList])
        else:
            documents = self.getDocumentsByName([emr.getSimpleDocumentName() for emr in emrList])

        order = {document.name: (document.type_order, document.type_name) for document in documents}
        unknown = (10000, "其它")

        type_orders = [v for k, v in order.items()]
        type_orders.sort()

        catalog, index = [], {}
        for type_id, type_name in type_orders:
            if type_id in index:
                continue
            catalog.append({
                'id': type_id,
                'name': type_name,
                'items': []
            })
            index[type_id] = len(catalog) - 1

        # 病程记录目录，将未识别的查房记录加入到此目录
        hos_course_order = 0
        for document in documents:
            if document.type_name == '病程记录':
                hos_course_order = document.type_order
                break

        for emr in emrList:
            # 忽略缺失文书
            if emr.docId == '0':
                continue
            emr_name = emr.getSimpleDocumentName()
            if self.app.config.get(Config.QC_DOCUMENT_CATALOG_FIELD) == "originType":
                emr_name = emr.getOriginType()

            # 文书对照到目录
            orderId, type_name = order.get(emr_name, unknown)

            # 未识别的查房记录加到病程记录目录中
            spical_words = ["查房记录", "日常病程记录", "病程记录"]
            if orderId == unknown[0] and True in [item in emr_name for item in spical_words]:
                orderId = hos_course_order
                order[emr_name] = (hos_course_order, '病程记录')

            if orderId in index:
                catalog[index[orderId]]['items'].append(emr.docId)
            else:
                catalog.append({
                    'id': orderId,
                    'name': type_name,
                    'items': [emr.docId]
                })
                index[orderId] = len(catalog) - 1
        return catalog

    def setRefuseDoctor(self, caseId, docId, doctor, operatorId, operatorName):
        """设置驳回医生

        Args:
            caseId ([type]): [description]
            docId ([type]): [description]
            doctor ([type]): [description]
        """
        with self.app.mysqlConnection.session() as session:
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            emrInfo = self._emrRepository.get(session, caseId, docId)
            if not emrInfo:
                return CommonResult(False, '未找到文书')
            origin_doctor_obj = self._doctorRepository.get(session, emrInfo.refuseCode)
            new_doctor_obj = self._doctorRepository.get(session, doctor)
            if origin_doctor_obj.model:
                log_content = f"{origin_doctor_obj.name}>{new_doctor_obj.name}"
            else:
                log_content = f"设置整改医生>{new_doctor_obj.name}"
            emrInfo.setRefuseDoctor(doctor)
            problems = self._problemRepository.getProblem(session, GetProblemListRequest(caseId=caseId, docId=docId))
            for p in problems:
                p.setModel(doctorCode=doctor)
            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, '设置整改医生',
                                             log_content, '', emrInfo.getDocumentName(), 'audit')
            return CommonResult(True)

    def batchSetRefuseDoctor(self, pids: List[int], doctor: str, operatorId, operatorName):
        """批量设置驳回医生
        """
        log_content_dict = dict()
        log_type_dict = dict()
        with self.app.mysqlConnection.session() as session:
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            new_doctor_obj = self._doctorRepository.get(session, doctor)
            problems = self._problemRepository.getByIds(session, pids)
            for p in problems:
                p.setModel(
                    doctorCode=doctor,
                )
                if p.emrInfoModel:
                    emrInfo = EmrDocument(p.emrInfoModel)
                    origin_doctor_obj = self._doctorRepository.get(session, emrInfo.refuseCode)
                    emrInfo.setRefuseDoctor(doctor)
                    if hasattr(origin_doctor_obj, "name"):
                        if not log_content_dict.get(emrInfo.docId):
                            log_content_dict[emrInfo.docId] = f'{origin_doctor_obj.name}>{new_doctor_obj.name}'
                    else:
                        log_content_dict[emrInfo.docId] = f'{emrInfo.getDocumentName()}>{new_doctor_obj.name}'
                    log_type_dict[emrInfo.docId] = emrInfo.getDocumentName()
            self._checkHistoryRepository.log(session, problems[0].caseId, operatorId, operatorName, '批量设置整改医生',
                                             '/'.join(log_content_dict.values()), '', '/'.join(log_type_dict.values()), 'audit')
            return CommonResult(True)

    def getRefuseDoctor(self, caseId: str, docId):
        """获取驳回医生

        Args:
            caseId (str): [description]
            docId ([type]): [description]
        """
        with self.app.mysqlConnection.session() as session:
            problem_count = self._problemRepository.getRefuseProblemCount(session, caseId, docId)
            fixDoctorFlag = 2 if problem_count > 0 else 1
            emrInfo = self._emrRepository.get(session, caseId, docId)
            if not emrInfo:
                return "", 2
            if not emrInfo.getRefuseDoctor():
                caseInfo = self._caseRepository.getByCaseId(session, caseId)
                if caseInfo:
                    return caseInfo.attendCode, fixDoctorFlag
            return emrInfo.getRefuseDoctor(), fixDoctorFlag

    def getEmrVersionByAudit(self, caseId: str, docId: str, auditId: int):
        """根据auditId获取对应的文书版本

        Args:
            caseId (str): [description]
            docId (str): [description]
            auditId (int): [description]
        """
        with self.app.mysqlConnection.session() as session:
            audit = self._auditRepository.get(session, auditId)
            doc = self._emrRepository.getEmrVersionByAudit(session, caseId, docId, audit)
            # 无法直接通过auditId获取到版本, 尝试根据时间匹配
            if doc is None:
                audit = self._auditRepository.get(session, auditId)
                if not audit:
                    raise ValueError(f'cannot find audit {auditId}')
                doc = self._emrRepository.getLastVersionBefore(session, caseId, docId, audit.applyTime)
                doc.expunge(session)
                return doc
            else:
                doc.expunge(session)
                return doc

    def getEmrDiffByAudit(self, caseId: str, docId: str, oldAuditId: int, newAuditId: int):
        """指定auditId的文书版本和当前版本diff
        """
        return self._emrRepository.diff(
            old=self.getEmrVersionByAudit(caseId, docId, oldAuditId),
            new=self.getEmrVersionByAudit(caseId, docId, newAuditId))

    def getCaseProblems(self, req: GetProblemListRequest):
        """问题列表
        """
        with self.app.mysqlConnection.session() as session:
            if not req.auditId:
                c = self._caseRepository.getByCaseId(session, req.caseId)
                if not c:
                    raise ValueError('case not found')
                req.auditId = c.audit_id
            problems = self.expunge(session, self._problemRepository.getProblem(session, req))
            count = len(problems)
            return problems, count

    def getProblemDetail(self, pid: int):
        """问题详情
        """
        with self.app.mysqlConnection.session() as session:
            row = self._problemRepository.get(session, pid)
            if row:
                row.expunge(session)
            return row

    def getCaseDoctors(self, req):
        """获取医生列表
        """
        with self.app.mysqlConnection.session() as session:
            if req.get('input'):
                if req.get('attendingFlag'):
                    return self.expunge(session, self._caseRepository.searchDoctor(session, req.get('input')))
                return self.expunge(session, self._doctorRepository.search(session, req.get('input')))
            elif req.get('caseId'):
                # 病历中的医生
                caseInfo = req.get("caseInfo", None)
                if not caseInfo:
                    caseInfo = self._caseRepository.getByCaseId(session, req.get('caseId'))
                doctorsDict = {caseInfo.attendCode: caseInfo.attendDoctor}
                # 文书中的医生
                emrList = req.get("emrList", None)
                if not emrList:
                    emrList = self._emrRepository.getEmrListByCaseId(session, req.get('caseId'))
                for emr in emrList:
                    emr_doctors = emr.getDoctors()
                    for d in emr_doctors:
                        doctorsDict[d.code] = d.name
                    doctorsDict[emr.refuseCode] = ""
                # 问题中的医生
                problems = req.get('problems', None)
                if not problems:
                    problems = self._problemRepository.getListByAuditId(session, caseInfo.audit_id)
                if problems:
                    for p in problems:
                        if p.doctorCode:
                            doctorsDict[p.doctorCode] = ""
                # 医生列表
                return self.expunge(session, self._doctorRepository.getByCodes(session, list(doctorsDict.keys())))
            else:
                return self.expunge(session, self._doctorRepository.search(session, req.get('input'), attendingFlag=req.get('attendingFlag'), department=req.get('department')))

    def GetCaseReason(self, caseId: str, ignoreAi=False, ignoreOnce=False, isFinal=False, isAddRefuse=0):
        """获取问题
        """
        with self.app.mysqlConnection.session() as session:
            caseInfo = self._caseRepository.getByCaseId(session, caseId)
            if not caseInfo:
                return
            problemReq = GetProblemListRequest(auditId=caseInfo.audit_id, ignoreAi=ignoreAi, auditType=self.auditType,
                                               isAddRefuse=isAddRefuse)
            problems = self.expunge(session, self._problemRepository.getProblem(session, problemReq))
            # TODO 只退一次的质控点
            onceQcItems = []
            result = []
            for p in problems:
                if (ignoreOnce and p.getQcItemId() in onceQcItems) or (p.qcItemModel and p.qcItemModel.enableType != 1 and not p.model.status):
                    continue
                result.append(p)
            return result

    @classmethod
    def get_qc_list_export_yaml(cls, patient_id_name, have_sample, audit_step, detailFields, fieldData=[], group_flag=0, auditType="", tag_hide=0):
        """
        动态获取质控列表导出详情配置
        :return:
        """
        is_hide_1, is_hide_2, is_hide_3 = "true", "true", "true"
        if detailFields.get("problem"):
            is_hide_1 = "false"
        if detailFields.get("score"):
            is_hide_2 = "false"
        if detailFields.get("firstPageScore"):
            is_hide_3 = "false"

        if not fieldData:
            reason_column = 9 if not group_flag else 10
            group_yaml = "" if not group_flag else "- name: 诊疗组\n"
            is_active = "false" if auditType != AUDIT_TYPE_ACTIVE else "true"
            data_yaml = QC_LIST_EXPORT_YAML.format(patient_name=patient_id_name, group=group_yaml, is_active=is_active)
            if is_active == "true":
                reason_column -= 1
            if auditType == AUDIT_TYPE_ACTIVE:
                data_yaml += QC_LIST_EXPORT_ACTIVE_DIAG_YAML
                reason_column += 4
            data_yaml += QC_LIST_EXPORT_ATTEND_DOCTOR_YAML
            data_yaml += QC_LIST_HAVE_SAMPLE_YAML if have_sample == 1 else QC_LIST_NO_SAMPLE_YAML
            if auditType == AUDIT_TYPE_ACTIVE:
                data_yaml += QC_LIST_ACTIVE_PROBLEM_INFO_YAML
                reason_column += 3
            reason_column += 3 if have_sample == 1 else 2
            if auditType != AUDIT_TYPE_ACTIVE:
                data_yaml += QC_LIST_IS_RECHECK_YAML if audit_step == "recheck" else QC_LIST_NO_RECHECK_YAML
                reason_column += 5 if audit_step == "recheck" else 3
            data_yaml += QC_LIST_EXPORT_END_YAML.format(is_hide_1=is_hide_1, is_hide_2=is_hide_2, is_hide_3=is_hide_3)
            if not tag_hide:
                data_yaml += "\ngroupFields:\n    - name: 重点病历"
            reason_column += 2
            return data_yaml, reason_column
        data_yaml = QC_LIST_EXPORT_TITLE_START_YAML
        for field in fieldData[1:]:
            data_yaml += "\n    - name: %s" % field
        data_yaml += QC_LIST_EXPORT_TITLE_END_YAML.format(is_hide_1=is_hide_1, is_hide_2=is_hide_2, is_hide_3=is_hide_3)
        data_yaml += "\n    - name: %s" % fieldData[0]
        return data_yaml, len(fieldData)

    def format_qc_list_export_data(self, caseList, request, have_sample, patient_id_name="病历号", group_flag=0, operation_data={}, diagnosis_data={}, tag_hide=0):
        """
        格式化抽取历史导出数据
        :return:
        """
        problem_dict = {}
        if request.detailFields.get("problem") or request.detailFields.get("score") or request.detailFields.get("firstPageScore"):
            case_id_list = [item.caseId for item in caseList]
            self.get_problem_dict(case_id_list, problem_dict, request.auditType)
        row_data = []
        data_yaml, reason_column = self.get_qc_list_export_yaml(patient_id_name, have_sample, request.auditStep,
                                                                request.detailFields, request.fieldData, group_flag,
                                                                auditType=request.auditType, tag_hide=tag_hide)

        if not caseList:
            tmp = dict(QC_LIST_EXPORT_DATA, **{patient_id_name: ""})
            row_data.append(tmp)
        for case_info in caseList:
            if request.auditType != AUDIT_TYPE_ACTIVE:
                audit_record = AuditRecord(case_info.auditRecord)
                problem_count = audit_record.getProblemCount(request.auditType)
                case_score = audit_record.getScore(request.auditType) or ""
                audit_doctor = audit_record.getReviewer(request.auditType, isFinal=False)[1] or ""
                audit_time = ""
                int_audit_time = 0
                if audit_record.getReviewTime(request.auditType, isFinal=False):
                    audit_time_str = audit_record.getReviewTime(request.auditType, isFinal=False)
                    audit_time = audit_time_str.strftime('%Y-%m-%d')
                    int_audit_time = int(audit_time_str.strftime('%Y-%m-%d-%H-%M-%S').replace("-", "") or 0)
                is_recheck = False if request.auditStep == "audit" else True
                status_name = parseStatusName(is_recheck, audit_record.getStatus(request.auditType),
                                              refused=case_info.refuseCount > 0)
                reviewer = audit_record.getReviewer(request.auditType, isFinal=True)[1] or ""
                review_time = ""
                if audit_record.getReviewTime(request.auditType, isFinal=True):
                    review_time = audit_record.getReviewTime(request.auditType, isFinal=True).strftime('%Y-%m-%d')
                receiveTime = audit_record.receiveTime.strftime("%Y-%m-%d") if audit_record.receiveTime else ""
                int_receiveTime = int(audit_record.receiveTime.strftime("%Y-%m-%d-%H-%M-%S").replace("-","") if audit_record.receiveTime else 0)
                operation = ""
                operationDays = 0
                diag = ""
                qc_num = 0
                activeManProblemNum = ""
                activeProblemStatus = ""
            else:
                case_score = float(case_info.activeAllScore or 100)
                problem_count = int(case_info.activeAllProblemNum or 0)
                active_record = case_info.active_record
                audit_doctor = active_record.operator_name if active_record else ""
                audit_time = active_record.create_time.strftime('%Y-%m-%d') if active_record and active_record.create_time else ""
                int_audit_time = int(active_record.create_time.strftime('%Y-%m-%d-%H-%M-%S').replace("-", "") if active_record and active_record.create_time else 0)
                status_name = ""
                reviewer = ""
                review_time = ""
                receiveTime = ""
                int_receiveTime = 0
                operationDays = 0
                diag = diagnosis_data.get(case_info.caseId) or case_info.diagnosis or ""
                operation = operation_data.get(case_info.caseId, {}).get("name") or ""
                oper_time = operation_data.get(case_info.caseId, {}).get("time")
                if oper_time:
                    operationDays = (datetime.now() - oper_time).days
                qc_num = case_info.activeQcNum or 0
                activeManProblemNum = case_info.activeProblemNum or 0
                activeProblemStatus = getActiveProblemStatus(case_info.activeProblemNoFixNum, case_info.activeProblemNum)

            assign_doctor = ""
            if case_info.sampleRecordItem:
                sampleRecord = SampleRecordItem(case_info.sampleRecordItem)
                assign_doctor = sampleRecord.getAssignExpert()[1] or ""  # 分配医生
            admitTime = case_info.admitTime.strftime("%Y-%m-%d") if case_info.admitTime else ""
            int_admitTime = int(case_info.admitTime.strftime("%Y-%m-%d-%H-%M-%S").replace("-", "") if case_info.admitTime else 0)
            dischargeTime = case_info.dischargeTime.strftime("%Y-%m-%d") if case_info.dischargeTime else ""
            int_dischargeTime = int(case_info.dischargeTime.strftime("%Y-%m-%d-%H-%M-%S").replace("-", "") if case_info.dischargeTime else 0)
            tags = ",".join([str(tag.name) for tag in case_info.TagsModel]) or ""  # 重点病历标签名
            inp_days = case_info.inpDays if case_info.dischargeTime else ((datetime.now() - case_info.admitTime).days if case_info.admitTime else 0)
            tmp = {"重点病历": tags, "问题数": problem_count, "分数": str(case_score), patient_id_name: case_info.inpNo or case_info.patientId,
                   "姓名": case_info.name or "", "科室": case_info.outDeptName or case_info.department or "", "病区": case_info.wardName or "",
                   "入院日期": admitTime, "admitTime": int_admitTime, "诊疗组": case_info.medicalGroupName or "",
                   "出院日期": dischargeTime, "dischargeTime": int_dischargeTime,
                   "住院天数": inp_days or 0, "责任医生": case_info.attendDoctor or "",
                   "质控医生": audit_doctor, "质控日期": audit_time, "auditTime": int_audit_time,
                   "签收日期": receiveTime, "receiveTime": int_receiveTime,
                   "状态": status_name, "分配医生": assign_doctor, "审核人": reviewer, "审核日期": review_time,
                   "返修次数": case_info.refuseCount or 0, "疾病": diag, "手术": operation, "手术后天数": operationDays,
                   "费用": '{:g}'.format(case_info.current_total_cost or 0), "质控次数": qc_num,
                   "人工问题数": activeManProblemNum, "人工问题状态": activeProblemStatus}

            problem_info = problem_dict.get(case_info.caseId, {})
            if request.detailFields.get("problem") or request.detailFields.get("score") or request.detailFields.get("firstPageScore"):
                tmp["问题描述"] = problem_info.get("reason", "")
                tmp["病案扣分"] = problem_info.get("score", "")
                tmp["首页扣分"] = problem_info.get("fp_score", "")
            row_data.append(tmp)
        return row_data, data_yaml, reason_column

    def get_problem_dict(self, case_id_list, problem_dict, audit_type):
        """
        根据caseId查询问题
        :return:
        """
        if not case_id_list:
            return
        case_ids = ','.join(['"%s"' % item for item in case_id_list])
        with self.app.mysqlConnection.session() as session:
            query_problem_score_sql = '''select c.caseId, cp.reason, cp.score, cp.problem_count, df.score, 
            cp.deduct_flag, cp.comment, ei.documentName, ei.first_save_time, cp.docId from caseProblem cp 
            inner join `case` c on cp.caseId = c.caseId and cp.audit_id = c.audit_id 
            left join dim_firstpagescore df on cp.qcItemId = df.qcitemid 
            left join emrInfo ei on cp.caseId = ei.caseId and cp.docId = ei.docId
            where cp.is_deleted = 0 and cp.auditType = "%s" and c.caseId in (%s)''' % (audit_type, case_ids)
            query = session.execute(query_problem_score_sql)
            queryset = query.fetchall()
            case_id_problem_dict = {}
            for item in queryset:
                score = item[2] or 0
                if item[5] != 1:
                    score = 0
                problem_count = item[3] or 1
                fp_score = item[4] or 0
                reason = item[1] or ""
                comment = item[6] or ""
                doc_name = item[7] or ""
                doc_save_time = item[8] or None
                doc_info = ""
                if str(item[9]) != "0":
                    if doc_name:
                        doc_info += "【" + doc_name
                    if doc_info:
                        if doc_save_time:
                            doc_info += doc_save_time.strftime("%Y-%m-%d") + "】"
                        else:
                            doc_info += "】"
                else:
                    doc_info = "【缺失文书】"
                reason_comment = doc_info + reason + "。" + comment
                i = case_id_problem_dict.get(item[0], 0)
                if not i:
                    i = 1
                    case_id_problem_dict[item[0]] = i
                if not problem_dict.get(item[0], None):
                    score1 = str(score * problem_count)
                    if len(score1) > 1 and score1[-1] == "0":
                        score1 = score1[:-2]
                    fp_score1 = str(fp_score * problem_count)
                    if len(fp_score1) > 1 and fp_score1[-1] == "0":
                        fp_score1 = score1[:-2]
                    problem_dict[item[0]] = {"reason": '''%s、%s''' % (i, reason_comment),
                                             "score": '''%s、扣%s分''' % (i, score1),
                                             "fp_score": '''%s、扣%s分''' % (i, fp_score1)}
                else:
                    problem_dict[item[0]]["reason"] += '''\n%s、%s''' % (i, reason_comment)
                    problem_dict[item[0]]["score"] += '''\n%s、扣%s分''' % (i, score * problem_count)
                    problem_dict[item[0]]["fp_score"] += '''\n%s、扣%s分''' % (i, fp_score * problem_count)
                case_id_problem_dict[item[0]] += 1

    def writeArchiveScoreExcel(self, sheet, caseList, patient_id_name="病历号"):
        """
        将case信息写入excel
        """
        title = ["重点病历", "病案分数", "病案等级", "首页分数", patient_id_name, "姓名", "出院科室", "出院病区", "入院日期", "出院日期", "责任医生", "状态"]
        for column in range(len(title)):
            sheet.cell(row=1, column=column + 1, value=str(title[column]))

        row_data = []
        for case_info in caseList:
            audit_record = AuditRecord(case_info.auditRecord)
            case_score = ''
            case_rating = ''
            fp_score = ''
            if audit_record:
                case_score = audit_record.getArchiveScore() or ""
                case_rating = parseRating(audit_record.getArchiveScore())
                fp_score = audit_record.getArchiveFPScore() or ""
            status_name = '已归档' if case_info.status == CASE_STATUS_ARCHIVED else ''
            tags = ",".join([str(tag.name) for tag in case_info.TagsModel]) or ""  # 重点病历标签名

            tmp = [tags, case_score, case_rating, fp_score, case_info.patientId, case_info.name or "",
                   case_info.outDeptName or "", case_info.wardName or "",
                   case_info.admitTime.strftime("%Y-%m-%d") if case_info.admitTime else "",
                   case_info.dischargeTime.strftime("%Y-%m-%d") if case_info.dischargeTime else "",
                   case_info.attendDoctor or "", status_name]
            row_data.append(tmp)

        for row in range(len(row_data)):
            for column in range(len(row_data[row])):
                sheet.cell(row=row + 2, column=column + 1, value=str(row_data[row][column]))

    def getCaseTag(self, input):
        """重点病历标签
        """
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self._caseTagRepository.getList(session, input))

    def getDocumentsByType(self, typeList):
        """获取文书对照
        """
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self._documentsRepository.getByStandardName(session, typeList))

    def getDocumentsByName(self, names):
        """获取文书对照
        """
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self._documentsRepository.getByName(session, names))

    def getProblemStats(self, req: GetProblemStatsRequest):
        with self.app.mysqlConnection.session() as session:
            return self._problemRepository.getCategoryStats(session, req)

    def getProblemStatsCase(self, req: GetProblemStatsRequest):
        with self.app.mysqlConnection.session() as session:
            tags = {t.code: t for t in self.expunge(session, self._caseTagRepository.getList(session, ''))}
            case_pstatus, total = self._problemRepository.getCategoryStatsCase(session, req)
            caseIds = [item.get('caseId') for item in case_pstatus]
            results = self._problemRepository.getCategoryStatsCaseDetail(session, caseIds)
            problem_data = self._problemRepository.getCategoryStatsProblem(session, req, caseIds)
            for item in results:
                item.convertTagToModel(tags)
                item.expunge(session)
            return results, total, case_pstatus, problem_data

    def getQcItems(self):
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self._qcItemRepository.getList(session, GetItemsListRequest()))

    def countEmrContent(self, caseId):
        with self.app.mysqlConnection.session() as session:
            return self._emrRepository.getEmrContentNum(session, caseId)

    def getAuditEmrInfo(self, caseId):
        """从AuditEmrInfo表中查询文书的修改历史，
        等同于从EmrContent表中查询，
        在每次保存文书有修改时创建AuditEmrInfo记录
        如果最后的结果里文书修改记录小于等于1
        """
        with self.app.mysqlConnection.session() as session:
            ret = dict()  # 返回每个文书的记录按照申请记录合并之后有多少个版本
            # 根据audit_record 记录的每次申请归档时间，划分时间段
            audit_periods = self._auditRepository.getAuditRecordPeriods(session, caseId)

            # 查询病历所有文书的修改记录，将每次修改根据时间落到申请记录时间范围中
            emr_record = self._emrRepository.getAuditEmrLog(session, caseId)
            for rec in emr_record:
                doc_id = rec.docId
                # data_id = rec.dataId
                create_time = arrow.get(rec.createTime)
                if ret.get(doc_id) is None:
                    ret[doc_id] = set()  # set 对相同申请AuditId去重
                for audit, start_time, end_time in audit_periods:
                    if start_time < create_time <= end_time:
                        ret[doc_id].add(audit.id)
            return ret

    def getCaseAssayList(self, req: GetAssayListRequest):
        """查询病历化验信息"""
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self._assayRepository.getAssayList(session, req))

    def getCaseExamList(self, req: GetExamListRequest):
        """查询病历检查信息"""
        with self.app.mysqlConnection.session() as session:
            results, total = self._examRepository.getExamList(session, req)
            for item in results:
                item.expunge(session)
            return (results, total) if req.withTotal else results

    def getCaseLabList(self, req: GetLabListRequest):
        """查询病历化验信息"""
        with self.app.mysqlConnection.session() as session:
            results, total = self._labRepository.getLabReportList(session, req)
            for item in results:
                item.expunge(session)
            return results, total

    def getScoreReport(self, caseId):
        with self.app.mysqlConnection.session() as session:
            caseInfo = self._caseRepository.getByCaseId(session, caseId)
            if not caseInfo:
                return
            case_detail = {
                'hospital': caseInfo.hospital or '',
                'department': caseInfo.outDeptName or caseInfo.department or '',
                'attending': caseInfo.attendDoctor or '',
                'patientname': caseInfo.name or '',
                'patientid': caseInfo.inpNo or caseInfo.patientId,
            }
            if self.auditType != AUDIT_TYPE_ACTIVE:
                if caseInfo.auditRecord is not None:
                    auditRecord = AuditRecord(caseInfo.auditRecord)
                    if auditRecord.getScore(self.auditType):
                        case_detail['casescore'] = '{:g}'.format(auditRecord.getScore(self.auditType))
                problemReq = GetProblemListRequest(auditId=caseInfo.audit_id, auditType=self.auditType)
                problems = self._problemRepository.getProblem(session, problemReq)
            else:
                problems = self._problemRepository.getDoctorProblem(session, caseId)
                total_score = 0
                for p in problems:
                    total_score += p.getScore()
                case_detail['casescore'] = '{:g}'.format(float(100 - total_score))
            # 从配置项中获取质控评分表模板名称，默认是浙江省人民医院提供的zhejiang2021
            tplcode = self.app.config.get(Config.QC_SCORE_REPORT_TEMPLATE) or 'zhejiang2021'
            scoreReporter = self._scoreReportRepository.get(session, tplcode)
            if not scoreReporter:
                logging.exception('none scoreReporter')
                report = "未找到质控评分表模板"
            else:
                report = scoreReporter.generateReport(case_detail, problems)
            return report

    def getMedicalAdvice(self, req):
        with self.app.mysqlConnection.session() as session:
            orders = self._orderRepository.search(session, req)
            for item in orders:
                item.expunge(session)
            return orders

    def getFirstPageInfo(self, caseId):
        with self.app.mysqlConnection.session() as session:
            row = self._caseRepository.getFirstPageInfo(session, caseId)
            if row:
                session.expunge(row)
            return row

    def getFixDoctorFlag(self, caseId, auditType):
        """
        查询是否可更改医生标识
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            doc_dict = self._problemRepository.getDocRefuseProblemCount(session, caseId, auditType)
        return doc_dict

    def getAIEmrData(self, caseId, docType):
        """
        # AI 接口获取文书内容数据
        select ei.*, ec.htmlContent, ec.contents, d.standard_name from emrInfo ei
        left join emrContent ec on ei.emrContentId = ec.id
        left join documents d on ei.documentName = d.name
        where ei.caseId = ? and ei.is_deleted = 0 and (d.standard_name in (?) or d.standard_name is None)
        """
        results = []
        with self.app.mysqlConnection.session() as session:
            emrInfo = self.app.mysqlConnection['emrInfo']
            emrContent = self.app.mysqlConnection['emrContent']
            documents = self.app.mysqlConnection['documents']

            handler = session.query(emrInfo, emrContent). \
                outerjoin(documents, documents.name == emrInfo.documentName). \
                outerjoin(emrContent, emrContent.id == emrInfo.emrContentId). \
                filter(emrInfo.caseId == caseId).filter(emrInfo.is_deleted == 0)
            if docType:
                dtypes = [t for t in docType if t]
                handler = handler.filter(or_(documents.standard_name.in_(dtypes), documents.standard_name.is_(None)))
            for row in handler.all():
                item = EmrDocument(row[0], row[1])
                results.append(item)
            self.expunge(session, results)
        return results

    def getTemperatureInfo(self, caseId):
        with self.app.mysqlConnection.session() as session:
            model = self.app.mysqlConnection['temperature_form']
            temperatureObjs = session.query(model).filter(model.caseId == caseId).all()
            result = []
            for obj in temperatureObjs:
                session.expunge(obj)
                result.append(obj)
            return result

    def getDiagnosisInfo(self, session=None, caseId=''):
        model = self.app.mysqlConnection['mz_diagnosis']
        if not session:
            with self.app.mysqlConnection.session() as session:
                diagnosisObjs = session.query(model).filter(model.caseId == caseId).order_by(text('diagId+0 asc'))
        else:
            diagnosisObjs = session.query(model).filter(model.caseId == caseId).order_by(text('diagId+0 asc'))
        result = []
        for obj in diagnosisObjs:
            session.expunge(obj)
            result.append(obj)
        return result

    def getFirstPageScoreDict(self):
        """
        查询病案首页扣分数据
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_sql = '''select qcitemid, score, maxscore from dim_firstpagescore'''
            query = session.execute(query_sql)
            data = query.fetchall()
            result = {}
            for obj in data:
                result[obj[0]] = {"score": obj[1], "max_score": obj[2]}
            return result

    def getCaseEmrParserResult(self, caseId):
        # 先从redis查找
        with Redis(connection_pool=self.app.redis_pool) as redis:
            data = redis.hgetall('formatted_data_' + caseId)
        if data:
            logging.info('find %s in redis' % caseId)
            result = dict()
            # 数据在redis中存在
            with self.app.mysqlConnection.session() as session:
                doc_ids = self._emrRepository.getDocIdList(session, caseId)
                for key, value in data.items():
                    key = key.decode('utf-8')
                    if key in doc_ids:
                        result[key] = json.loads(value.decode('utf-8'))
                return result
        else:
            # 从mysql中查找
            with self.app.mysqlConnection.session() as session:
                result = self._emrRepository.getParserResult(session, caseId)
            return result

    def getExternalLinks(self):
        result = []
        with self.app.mysqlConnection.session() as session:
            for link in self._externalLinkRepo.getList(session):
                session.expunge(link)
                result.append(link)
        return result

    def getCaseDiagnosis(self, caseIds, isMz=False):
        """
        查询病历主诊断
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            return self._caseRepository.getCaseDiagnosisByCaseId(session, caseIds, isMz=isMz)

    def getCaseOperationData(self, caseIds):
        """
        查询病历最近手术信息
        :param caseIds:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            return self._caseRepository.getCaseOperationByCaseId(session, caseIds)

    def active_save(self, request, doctorName):
        """
        事中质控-保存质控结果
        1. 记录保存记录
        2. 记录check history记录
        3. 发送消息到指定医生
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            case_info = self._caseRepository.getByCaseId(session, request.caseId)
            active_id = self._caseRepository.save_active_info(session, request, doctorName)
            self._caseRepository.update_case_active_id(session, request.caseId, active_id)
            self._caseRepository.update_case_problem_save_flag(session, request.problems)
            self._checkHistoryRepository.log(session, request.caseId, request.operatorId, doctorName, action="保存", content="", comment="", auditType=request.auditType)
            msg = {
                "caseId": request.caseId,
                "send_user": doctorName,
                "message": "【{name}】被{operatorName}质控，共添加{num}个问题，请及时整改！".format(name=case_info.name, operatorName=doctorName, num=len(request.problems)),
                "receive_user": case_info.attendCode,
                "tipType": 1, #1-闪退, 2-常驻, 3-拦截
            }
            self._messageRepository.send(msg)
            qcItemIds = self._problemRepository.getQcItemIdByProblemIds(session, list(request.problems))
            for qcItemId in qcItemIds:
                self._problemRepository.recordProblemAction(session, request.caseId, qcItemId, "发送问题", request.operatorId, doctorName, request.auditType)

    def getProblemRecordList(self, request):
        """
        查询问题日志列表
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            data = self._problemRepository.getRecordList(session, request)
            # 当前audit_id下每个质控点出现的次数
            current_audit_problem_num = defaultdict(int)
            # 当前audit_id下每个质控点的删除标记的和
            current_audit_problem_delete_sum = defaultdict(int)
            for item in data:
                if item.cp_audit_id == item.c_audit_id:
                    current_audit_problem_num[item.qcItemId] += 1
                    current_audit_problem_delete_sum[item.qcItemId] += item.is_deleted
            # 当前现存质控点
            current_audit_problem = []
            for qcItemId in current_audit_problem_num:
                # 次数与删除标记和做对比, 相同则全部删除状态, 该质控点为已解决, 次数>删除标记和, 则存在未删除状态, 该质控点为现存
                if current_audit_problem_num[qcItemId] > current_audit_problem_delete_sum[qcItemId]:
                    current_audit_problem.append(qcItemId)
            qcItemId_data_dict = {}
            for item in data:
                existFlag = 1 if item.qcItemId in current_audit_problem else 0  # 1-现存, 0-已解决
                setattr(item, "existFlag", existFlag)
                ch_audit_type = EXPORT_FILE_AUDIT_TYPE.get(item.auditType) + "质控"
                if request.problemStatus:
                    if request.problemStatus == 1:
                        if item.existFlag == 1:
                            if qcItemId_data_dict.get(item.qcItemId) and ch_audit_type not in qcItemId_data_dict[item.qcItemId].auditType:
                                qcItemId_data_dict[item.qcItemId].auditType += "," + ch_audit_type
                            else:
                                item.auditType = ch_audit_type
                                qcItemId_data_dict[item.qcItemId] = item
                    elif request.problemStatus == 2:
                        if item.existFlag == 0:
                            if qcItemId_data_dict.get(item.qcItemId) and ch_audit_type not in qcItemId_data_dict[item.qcItemId].auditType:
                                qcItemId_data_dict[item.qcItemId].auditType += "," + ch_audit_type
                            else:
                                item.auditType = ch_audit_type
                                qcItemId_data_dict[item.qcItemId] = item
                    continue
                if qcItemId_data_dict.get(item.qcItemId) and ch_audit_type not in qcItemId_data_dict[item.qcItemId].auditType:
                    qcItemId_data_dict[item.qcItemId].auditType += "," + ch_audit_type
                else:
                    item.auditType = ch_audit_type
                    qcItemId_data_dict[item.qcItemId] = item
            res = []
            for key, value in qcItemId_data_dict.items():
                # auditType的过滤不能在查询时，因为可能存在多个节点质控出同一个qcItemId，导致查询过滤后仅剩一个
                if request.auditType:
                    ch_audit_type = EXPORT_FILE_AUDIT_TYPE.get(request.auditType) + "质控"
                    if ch_audit_type in value.auditType:
                        res.append(value)
                    continue
                res.append(value)
            total = len(res)
            start = request.start or 0
            size = request.size or 15
            res = res[start: start + size]
            return res, total

    def getProblemRecordDetail(self, request):
        """
        问题日志详情
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            return self._problemRepository.getProblemRecordDetail(session, request)

    def urgeRefusedCase(self, caseIds):
        with self.app.mysqlConnection.session() as session:
            for caseId in caseIds:
                row = self._caseRepository.getByCaseId(session, caseId)
                audit_record = AuditRecord(row.auditRecord)
                audit_record.setUrgeFlag()


class DepartmentCaseApplication(CaseApplication):

    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_DEPARTMENT)


class HospitalCaseApplication(CaseApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_HOSPITAL)


class ExpertCaseApplication(CaseApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_EXPERT)


class FirstpageCaseApplication(CaseApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_FIRSTPAGE)


class ActiveCaseApplication(CaseApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_ACTIVE)
