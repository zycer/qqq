# #!/usr/bin/env python3
# '''
# Author: qiupengfei@rxthinking.com
# Date: 2021-04-07 13:12:14

# 继承grpc生成的servicer类, 实现相关接口

# '''
# import base64
# import json
# import logging
# import os
# import random
# import threading
# import time
# import uuid
# from datetime import datetime

# import arrow
# import openpyxl
# from iyoudoctor.hosp.qc.v3.qcaudit.service_pb2_grpc_wrapper import QCManagerServicer as _QCManagerServicer
# from iyoudoctor.hosp.qc.v3.qcaudit.service_message_pb2 import CommonResponse, GetCaseListResponse, \
#     GetCaseDetailResponse, GetCaseProblemResponse, CheckProblemResponse, CheckEmrResponse, GetCaseDoctorsResponse, \
#     GetCaseReasonResponse, GetRefuseDoctorResponse, CheckCaseRequest, GetCaseCheckHistoryResponse, \
#     GetMedicalAdviceResponse, GetCaseTimelineResponse, GetRefusedProblemResponse, GetBranchResponse, GetWardResponse, \
#     GetDepartmentResponse, GetCaseTagResponse, GetAuditStatusResponse, GetDoctorsResponse, GetReviewersResponse, \
#     GetStandardEmrResponse, GetCaseQcItemsResponse, GetInpatientListResponse, GetCaseEmrListResponse, \
#     GetEmrVersionResponse, GetEmrDiffResponse, GetCaseEmrResponse, AddCaseProblemRequest, GetAdviceTypeResponse, \
#     GetConfigItemsResponse, GetCaseExportResponse, DownloadFileResponse, GetEmrDataResponse, GetDiagnosisResponse, \
#     GetCaseDeductDetailResponse, GetOperationResponse, GetQCReportResponse, GetDiseaseResponse, \
#     GetCaseLabExamInfoResponse, ExternalSystemLinksResponse, \
#     GetCaseLabResponse, GetCaseExamResponse, GetCalendarResponse, GetConfigListResponse, CaseGroupListResponse, \
#     ProblemRecordListResponse, ProblemRecordDetailResponse, CommonBatchResponse
# from sqlalchemy import or_

# from qcaudit.config import Config
# from qcaudit.common.const import AUDIT_STATUS, RECHECK_STATUS, EXPORT_FILE_AUDIT_TYPE, EXPORT_FILE_AUDIT_STEP, \
#     CASE_LIST_PROBLEM_COUNT, CASE_STATUS_ARCHIVED, CASE_LIST_AUDIT_TIME, CASE_LIST_AUDIT_DOCTOR, CASE_LIST_CASE_SCORE, \
#     AUDIT_TYPE_ACTIVE
# from qcaudit.domain.audit.auditrecord import AuditRecord
# from qcaudit.domain.case.case import CaseType
# from qcaudit.domain.case.emr import EmrDocument
# from qcaudit.domain.case.req import GetCaseListRequest, GetEmrListRequest, GetOrderListRequest, GetAssayListRequest, GetExamListRequest
# from qcaudit.domain.doctor.appeal_repository import AppealRepository
# from qcaudit.domain.lab.req import GetLabListRequest
# from qcaudit.domain.problem.problem import ProblemSumTags
# from qcaudit.domain.problem.req import GetProblemListRequest
# from qcaudit.domain.qcgroup.qcitem import QcItem
# from qcaudit.domain.qcgroup.qcitem_req import GetItemsListRequest
# from qcaudit.domain.req import SortField
# from qcaudit.service.sample_archive_job import SampleArchiveJob
# from qcaudit.service.ip_rule_service import IpBlockService
# from qcaudit.service.protomarshaler import unmarshalCaseInfo, unmarshalProblem, unmarshalCheckHistory, \
#     unmarshalMedicalAdvice, unmarshalAuditTimeline, unmarshalCaseEmr, setRequestStatus, parseGender, \
#     unmarshalDiffProblem, parseRating, unmarshalProblemSumTags, \
#     unmarshalLabReport, unmarshalExamination, parseStatus, unmarshalProblemRecordList, unmarshalProblemRecordDetail
# from qcaudit.utils.bidataprocess import BIFormConfig, BIDataProcess
# from qcaudit.utils.towebconfig import QC_LIST_SORT_DICT, SORT_DESC_DICT
# from iyoudoctor.internals.framework import Invocation
# from qcaudit.service.calendar_service import CalendarService
# from qcaudit.domain.user.user import User
# from google.protobuf.struct_pb2 import Struct


# class AuditService(_QCManagerServicer):

#     def __init__(self, context):
#         self.context = context
#         self.export_path = "/tmp/"
#         self.calendarSvc = CalendarService(context)
#         self.ipBlockSvc = IpBlockService(context)
#         self.archive_task = None
#         self._check_archive_task()

#     def _check_archive_task(self):
#         if self.archive_task and self.archive_task.is_alive():
#             return
#         archive_job = SampleArchiveJob(self.context)
#         self.archive_task = threading.Thread(target=archive_job.task)
#         self.archive_task.start()
#         self.archive_task.join(0)

#     def GetCaseList(self, request, context):
#         """获取病历列表
#         """
#         response = GetCaseListResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         field, pList = app.getDeptPermission(request.operatorId)
#         logging.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')

#         req = self.get_case_list_req(app, request, field=field, p_list=pList)
#         caseList, total = app.getCaseList(req)
#         operation_data = {}
#         diagnosis_data = {}
#         if request.auditType == AUDIT_TYPE_ACTIVE:
#             caseIds = [item.caseId for item in caseList]
#             operation_data = app.getCaseOperationData(caseIds)
#             diagnosis_data = app.getCaseDiagnosis(caseIds, isMz=True)
#         count = 0
#         for x in caseList:
#             protoItem = response.items.add()
#             unmarshalCaseInfo(x, protoItem, request.auditType, isFinal=request.auditStep == "recheck", diagnosis_data=diagnosis_data, operation_data=operation_data)
#             if app.app.config.get(Config.QC_AUDIT_ONLY_RECEIVED.format(auditType=request.auditType)) == '1':
#                 # 当前节点配置项只允许质控已签收的病历时，没有签收时间的病历视为未签收
#                 protoItem.notReceive = int(protoItem.receiveTime == "")
#             count += 1
#         response.total = total
#         response.start = request.start + count
#         response.size = request.size
#         return response

#     @classmethod
#     def get_case_list_req(cls, app, request, is_export=0, field='', p_list=list()):
#         """
#         查询病历列表条件获取
#         :return:
#         """
#         params = ["branch", "ward", "department", "attend", "rating",
#                   "caseId", "patientId", "reviewer", "problemFlag", "patientName",
#                   "autoReviewFlag", "firstPageFlag", "start", "size",
#                   "auditType", "auditStep", "startTime", "endTime", "caseType", "deptType", "timeType",
#                   "diagnosis", "operation", "archiveRating", "refuseCount", "group", "category",
#                   "minScore", "maxScore", "minCost", "maxCost", "activeQcNum", "activeManProblemNum", "activeProblemStatus",
#                   "minDays", "maxDays"]
#         req = {c: getattr(request, c) for c in params if hasattr(request, c)}
#         req['pField'] = field
#         req['pList'] = p_list
#         req['onlineStartTime'] = app.app.config.get(Config.QC_FIRST_ONLINE_PUBLISH_TIMESTAMP, '')
#         setRequestStatus(req, request.auditType, request.auditStep, status=request.status)
#         req["is_export"] = is_export
#         if request.caseType == 'running':
#             req['includeCaseTypes'] = [CaseType.ACTIVE]
#         elif request.caseType == 'archived':
#             req['includeCaseTypes'] = [CaseType.ARCHIVE]
#         elif request.caseType == 'Final':
#             req['includeCaseTypes'] = [CaseType.FINAL]
#         # 排序
#         if request.sortField:
#             dept = 'outDeptName' if request.auditType != AUDIT_TYPE_ACTIVE else "department"
#             # 抽取顺序
#             FIELD_MAP = {
#                 'department': dept,
#                 'ward': 'wardName',
#                 'attending': 'attendDoctor',
#                 'branch': 'branch',
#                 'problems': CASE_LIST_PROBLEM_COUNT,
#                 'tags': 'tags',
#                 'receiveTime': 'receiveTime',
#                 'admitTime': 'admitTime',
#                 'auditTime': CASE_LIST_AUDIT_TIME,
#                 'dischargeTime': 'dischargeTime',
#                 'problemCount': CASE_LIST_PROBLEM_COUNT,
#                 'auditDoctor': CASE_LIST_AUDIT_DOCTOR,
#                 'caseScore': CASE_LIST_CASE_SCORE,
#                 'activeManProblemNum': 'now_problem_num',
#                 'activeProblemStatus': 'problem_all_num - no_fix_problem_num',
#             }
#             req['sortFields'] = []
#             if request.auditType == 'department':
#                 req['sortFields'] = [SortField(field='urgeFlag', way='DESC', table='audit_record')]
#             for sf in request.sortField:
#                 if FIELD_MAP.get(sf.field):
#                     if sf.field == 'receiveTime':
#                         sort_field = SortField(field=FIELD_MAP.get(sf.field, sf.field), way=sf.way,
#                                                table='audit_record', extParams=sf.extParams)
#                     elif sf.field == "problems" or sf.field == "problemCount":
#                         sort_field = SortField(field=FIELD_MAP.get(sf.field)[request.auditType], way=sf.way,
#                                                extParams=sf.extParams)
#                     elif sf.field == "auditTime":
#                         table = 'audit_record' if request.auditType != AUDIT_TYPE_ACTIVE else "active_record"
#                         sort_field = SortField(field=FIELD_MAP.get(sf.field)[request.auditType], way=sf.way,
#                                                table=table, extParams=sf.extParams)
#                     elif sf.field == "auditDoctor":
#                         table = 'audit_record' if request.auditType != AUDIT_TYPE_ACTIVE else "active_record"
#                         sort_field = SortField(field=FIELD_MAP.get(sf.field)[request.auditType],
#                                                way=sf.way, table=table, extParams=sf.extParams)
#                     elif sf.field == "caseScore":
#                         sort_field = SortField(field=FIELD_MAP.get(sf.field)[request.auditType], way=sf.way,
#                                                table='audit_record', extParams=sf.extParams)
#                     else:
#                         sort_field = SortField(field=FIELD_MAP.get(sf.field, sf.field), way=sf.way,
#                                                extParams=sf.extParams)
#                     req['sortFields'].append(sort_field)
#         else:
#             # 默认排序
#             sort_field = 'dischargeTime' if request.auditType != AUDIT_TYPE_ACTIVE else 'admitTime'
#             # 科室质控将催办的病历置顶
#             if request.auditType == 'department':
#                 req['sortFields'] = [SortField(field='urgeFlag', way='DESC', table='audit_record'), SortField(field=sort_field, way='DESC')]
#             else:
#                 req['sortFields'] = [SortField(field=sort_field, way='DESC')]
#         req['isFinal'] = request.auditStep == "recheck"
#         if request.assignDoctor:
#             req['sampleExpert'] = request.assignDoctor
#         if app.app.config.get(Config.QC_PRECONDITION.format(auditType=request.auditType)):
#             req["precondition"] = app.app.config.get(Config.QC_PRECONDITION.format(auditType=request.auditType))
#         req["not_apply"] = app.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType=request.auditType))
#         if app.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=request.auditType)) == '1':
#             req["openSampleFlag"] = True
#             req["sampleArchiveFlag"] = app.app.config.get(Config.QC_SAMPLE_ARCHIVE.format(auditType=request.auditType)) == '1'
#         if request.tag:
#             req['tags'] = [tag for tag in request.tag.split(',') if tag]
#         req['timeType'] = int(request.timeType) if request.timeType else 0
#         req['visitType'] = request.visitType or app.app.config.get(Config.QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE, '')
#         req['fixOvertimeFlag'] = request.fixOvertimeFlag or 0
#         if request.overtime:
#             req['overtime'] = request.overtime
#         req = GetCaseListRequest(**req)
#         return req

#     def GetCaseDetail(self, request, context):
#         """获取病历详情
#         """
#         response = GetCaseDetailResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             logging.info("GetCaseDetail, caseId: %s is not exist.", request.caseId)
#             return response
#         isMz = True if request.auditType == AUDIT_TYPE_ACTIVE else False
#         diagnosis = app.getCaseDiagnosis([request.caseId], isMz=isMz)
#         unmarshalCaseInfo(caseInfo, response.basicInfo, request.auditType, isFinal=request.auditStep == 'recheck', diagnosis_data=diagnosis)
#         # 快照需要查询 originCase.dischargeTime 判断是否已经出院
#         if caseInfo.getCaseType == CaseType.SNAPSHOT:
#             originCaseInfo = app.getCaseDetail(caseInfo.originCaseId)
#             if not originCaseInfo:
#                 return
#             response.basicInfo.dischargeTime = originCaseInfo.dischargeTime.strftime('%Y-%m-%d') if originCaseInfo.dischargeTime else ""
#         response.basicInfo.readOnly = request.readOnly
#         return response

#     def GetCaseProblem(self, request, context):
#         """获取质控问题列表
#         """

#         def getProblemTags(problem):
#             if not problem:
#                 return []
#             t = problem.getTags()
#             if problem.qcItemModel:
#                 t.extend(QcItem(problem.qcItemModel).getTags())
#             return t

#         response = GetCaseProblemResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         # reqDict = MessageToDict(request)
#         isFinal = request.auditStep == "recheck"
#         caseInfo = app.getCaseDetail(caseId=request.caseId)
#         if not caseInfo:
#             return
#         reqDict = {c: getattr(request, c) for c in ['id', 'caseId', 'docId', 'auditType', 'nowStatusFlag']}
#         reqDict["auditId"] = caseInfo.audit_id
#         reqDict["caseStatus"] = caseInfo.status
#         reqDict["refuseCount"] = caseInfo.refuseCount or 0
#         problems, total = app.getCaseProblems(GetProblemListRequest(**reqDict))
#         # 统计
#         response.summary.total = 0
#         response.summary.addByDr = 0
#         response.summary.confirmed = 0
#         deductSum = 0  # 问题扣分总和
#         problem_id_list = []
#         problems_sum_tags = ProblemSumTags()
#         for p in problems:
#             problem_id_list.append(p.id)
#             response.summary.total += p.getProblemCount()
#             if not p.fromAi():
#                 response.summary.addByDr += p.getProblemCount()
#             else:
#                 response.summary.confirmed += p.getProblemCount()
#             deductSum += float(p.getScore() if p.getDeductFlag() else 0)
#             if p.qcItemModel:
#                 qcitem = QcItem(p.qcItemModel)
#                 if qcitem.isSingleDisease():
#                     response.summary.singleCount += p.getProblemCount()
#                 if qcitem.isVeto():
#                     response.summary.vetoCount += p.getProblemCount()
#             # 问题列表标签统计
#             problems_sum_tags.add_sum_tags(tags=getProblemTags(p), count=p.getProblemCount())
#         # 问题标签统计
#         unmarshalProblemSumTags(response.sumtags, problems_sum_tags)
#         # 总扣分
#         response.deductSum = '{:g}'.format(float(deductSum))
#         # 文书列表和对应的标准文书名称
#         emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000), withNoDocOption=False)
#         documents = app.getDocumentsByName([emr.documentName.strip() for emr in emrList])
#         dorder = {document.name: document.type_order for document in documents}
#         dtypes = {document.type_order: document.type_name for document in documents}
#         appeal = AppealRepository(self.context.app, request.auditType)
#         have_appeal_dict = appeal.get_appeal_dict(problem_id_list, caseId=request.caseId)
#         fix_doctor_flag_dict = app.getFixDoctorFlag(request.caseId, request.auditType)
#         firstpage_score_dict = {}
#         if request.nowStatusFlag:
#             firstpage_score_dict = app.getFirstPageScoreDict()
#         # 返回值
#         if not request.tabIndex:
#             for p in problems:
#                 protoItem = response.items.add()
#                 unmarshalProblem(p, protoItem, request.auditType, have_appeal_dict=have_appeal_dict)
#         elif request.tabIndex == 1:
#             case_audit_status = 3
#             if not request.nowStatusFlag and request.auditType != AUDIT_TYPE_ACTIVE:
#                 if caseInfo.auditRecord:
#                     audit = AuditRecord(caseInfo.auditRecord)
#                     auditScore = audit.getScore(request.auditType)
#                     problemCount = audit.getProblemCount(request.auditType)
#                     if not auditScore and not problemCount:
#                         auditScore = 100.0
#                     response.caseScore = '{:g}'.format(auditScore)
#                     response.caseRating = parseRating(auditScore)
#                     response.lostScore = '{:g}'.format(float(100 - auditScore))
#                     if audit.getFirstPageScore(request.auditType):
#                         response.firstpageScore = '{:g}'.format(audit.getFirstPageScore(request.auditType))
#                     case_audit_status = parseStatus(isFinal, audit.getStatus(request.auditType, isFinal))
#             else:
#                 # 病历现状/事中质控 不使用统计后的分数, 需根据问题统计

#                 response.lostScore = '{:g}'.format(float(deductSum))
#                 response.caseScore = '{:g}'.format(100 - float(deductSum))
#                 response.caseRating = parseRating(response.caseScore)

#             # 排序和文书列表保持一致
#             if int(app.app.config.get(Config.QC_EMR_SORT) or 1) == 2:
#                 emrList.sort(key=lambda data: data.recordTime if data.recordTime else data.createTime or datetime.now())
#             else:
#                 documents = app.getDocumentsByName([emr.documentName.strip() for emr in emrList])
#                 order = {document.name: document.type_order for document in documents}
#                 emrList.sort(key=lambda data: order.get(data.documentName.strip(), 10000))
#             fp_lost_score = 0
#             for emr in emrList:
#                 docId = emr.docId
#                 fixDoctorFlag = fix_doctor_flag_dict.get(docId, 2)
#                 groupAdded = False  # 每个文书创建一个groups
#                 group = None
#                 for p in problems:
#                     # 问题状态
#                     p_status = p.checkProblemStatus()
#                     # 问题标签
#                     tags = getProblemTags(p)
#                     if request.tag and request.tag not in tags:
#                         continue
#                     # 问题分组
#                     if p.docId and p.docId == docId:
#                         if not groupAdded:
#                             group = response.groups.add()
#                             group.summary.total = 0
#                             group.summary.lostScore = '0'
#                             group.docId = p.docId
#                             group.docName = p.emrInfoModel.documentName if p.emrInfoModel and p.emrInfoModel.documentName else p.title
#                             group.createTime = p.emrInfoModel.recordTime.strftime('%Y-%m-%d %H:%M') if p.emrInfoModel and p.emrInfoModel.recordTime else ""
#                             group.doctorCode = p.emrInfoModel.refuseCode if p.emrInfoModel and p.emrInfoModel.refuseCode else ""
#                             group.doctor = p.doctor or ""
#                             group.fixDoctorFlag = fixDoctorFlag
#                             groupAdded = True
#                             if "病案首页" in emr.documentName:
#                                 group.isFirstPage = 1

#                         group.summary.total += p.getProblemCount()
#                         group.summary.auditProblemNum += p_status
#                         group.summary.tipProblemNum += (1 - p_status)
#                         group.summary.lostScore = '{:g}'.format(float(group.summary.lostScore) + float(p.getScore() if p.getDeductFlag() else 0))
#                         item = group.problems.add()
#                         unmarshalProblem(p, item, request.auditType, have_appeal_dict=have_appeal_dict)
#                         item.catalogId = dorder.get(emr.documentName.strip(), 0)  # 文书目录id
#                         item.catalog = dtypes.get(item.catalogId, '')
#                         if request.auditType == AUDIT_TYPE_ACTIVE:
#                             # 事中质控的人工问题均可随时修改, AI问题不可修改
#                             item.editStatus = 2 if request.readOnly or p.fromAi() else 1
#                         else:
#                             item.editStatus = 2 if request.readOnly or p.refuseFlag == 1 or case_audit_status == 3 else 1
#                         item.fixDoctorFlag = fixDoctorFlag
#                         # 单独计算病案首页文书问题扣分情况
#                         fp_score_max = firstpage_score_dict.get(p.qcItemId, {}).get("max_score", 0)
#                         fp_score = firstpage_score_dict.get(p.qcItemId, {}).get("score", 0) * (p.problem_count or 0)
#                         fp_lost_score += min(fp_score, fp_score_max)
#             if request.nowStatusFlag:
#                 response.firstpageScore = '{:g}'.format(100 - fp_lost_score)
#             group = None
#             for p in problems:
#                 # 问题标签
#                 tags = getProblemTags(p)
#                 p_status = p.checkProblemStatus()
#                 if request.tag and request.tag not in tags:
#                     continue
#                 if p.docId and p.docId == "0":
#                     fixDoctorFlag = fix_doctor_flag_dict.get(p.docId, 2)
#                     if not group:
#                         group = response.groups.add()
#                         group.docName = "文书缺失"
#                         group.docId = "0"
#                         group.summary.lostScore = '0'
#                         group.fixDoctorFlag = fixDoctorFlag
#                     group.summary.total += p.getProblemCount()
#                     group.summary.auditProblemNum += p_status
#                     group.summary.tipProblemNum += (1 - p_status)
#                     group.summary.lostScore = '{:g}'.format(float(group.summary.lostScore) + float(p.getScore() if p.getDeductFlag() else 0))
#                     item = group.problems.add()
#                     unmarshalProblem(p, item, request.auditType, have_appeal_dict=have_appeal_dict)
#                     if request.auditType == AUDIT_TYPE_ACTIVE:
#                         # 事中质控的人工问题均可随时修改, AI问题不可修改
#                         item.editStatus = 2 if request.readOnly or p.fromAi() else 1
#                     else:
#                         item.editStatus = 2 if request.readOnly or p.refuseFlag == 1 or case_audit_status == 3 else 1
#                     item.fixDoctorFlag = fixDoctorFlag
#         elif request.tabIndex == 2:
#             case_audit_status = 3
#             if not request.nowStatusFlag:
#                 if caseInfo.auditRecord:
#                     audit = AuditRecord(caseInfo.auditRecord)
#                     auditScore = audit.getScore(request.auditType)
#                     problemCount = audit.getProblemCount(request.auditType)
#                     if not auditScore and not problemCount:
#                         auditScore = 100.0
#                     response.caseScore = '{:g}'.format(auditScore)
#                     response.caseRating = parseRating(auditScore)
#                     response.lostScore = '{:g}'.format(float(100 - auditScore))
#                     if audit.getFirstPageScore(request.auditType):
#                         response.firstpageScore = '{:g}'.format(audit.getFirstPageScore(request.auditType))
#                     case_audit_status = parseStatus(isFinal, audit.getStatus(request.auditType, isFinal))
#             else:
#                 # 病历现状不使用统计后的分数, 需根据问题统计
#                 response.lostScore = '{:g}'.format(float(deductSum))
#                 response.caseScore = '{:g}'.format(100 - float(deductSum))
#                 response.caseRating = parseRating(response.caseScore)
#             for p in problems:
#                 if not p.doctorCode:
#                     p.doctorCode = caseInfo.attendCode
#                     p.doctor = caseInfo.attendDoctor
#             emrList.append(EmrDocument(self.context.getEmrRepository(request.auditType).emrInfoModel(docId='0', documentName='缺失文书')))
#             doctors = app.getCaseDoctors({'caseId': request.caseId, "caseInfo": caseInfo, "emrList": emrList,
#                                           "problems": problems})
#             orderedDoctor = []
#             if doctors:
#                 doctors = {doctor.id: doctor for doctor in doctors}
#                 for (code, d) in doctors.items():
#                     count = 0
#                     for p in problems:
#                         if p.doctorCode and p.doctorCode == code:
#                             count += p.getProblemCount()
#                     if count > 0:
#                         orderedDoctor.append([code, count])
#             orderedDoctor.sort(key=lambda data: data[1], reverse=True)
#             # 按照文书排序
#             preOrderedProblems = []
#             for emr in emrList:
#                 for p in problems:
#                     if p.docId and p.docId == emr.docId:
#                         preOrderedProblems.append(p)
#             fp_lost_score = 0
#             # 按照医生问题数排序
#             for d in orderedDoctor:
#                 groupAdded = False
#                 group = None
#                 for p in preOrderedProblems:
#                     # 问题标签
#                     tags = getProblemTags(p)
#                     if request.tag and request.tag not in tags:
#                         continue
#                     doctorCode = p.doctorCode if p.doctorCode else caseInfo.attendCode
#                     doctorName = doctors.get(p.doctorCode).name if doctors.get(p.doctorCode) else caseInfo.attendDoctor
#                     fixDoctorFlag = fix_doctor_flag_dict.get(p.docId, 2)
#                     if doctorCode == d[0]:
#                         if not groupAdded:
#                             group = response.groups.add()
#                             group.summary.total = 0
#                             group.summary.lostScore = '0'
#                             group.doctorCode = doctorCode
#                             group.doctor = doctorName
#                             group.department = doctors.get(doctorCode).department if doctors.get(doctorCode) else ""
#                             group.fixDoctorFlag = fixDoctorFlag
#                             groupAdded = True
#                             title = p.title or ''
#                             if not title and p.emrInfoModel:
#                                 title = p.emrInfoModel.documentName
#                             if "病案首页" in title:
#                                 group.isFirstPage = 1
#                         group.summary.total += p.getProblemCount()
#                         group.summary.lostScore = '{:g}'.format(float(group.summary.lostScore) + float(p.getScore() if p.getDeductFlag() else 0))
#                         item = group.problems.add()
#                         unmarshalProblem(p, item, request.auditType, have_appeal_dict=have_appeal_dict)
#                         if p.emrInfoModel:
#                             item.catalogId = dorder.get(p.emrInfoModel.documentName.strip(), 0)  # 文书目录id
#                             item.catalog = dtypes.get(item.catalogId, '')
#                         item.editStatus = 2 if request.readOnly or p.refuseFlag == 1 or case_audit_status == 3 else 1
#                         item.fixDoctorFlag = fixDoctorFlag
#                         fp_score_max = firstpage_score_dict.get(p.qcItemId, {}).get("max_score", 0)
#                         fp_score = firstpage_score_dict.get(p.qcItemId, {}).get("score", 0) * (p.problem_count or 0)
#                         fp_lost_score += min(fp_score, fp_score_max)
#             if request.nowStatusFlag:
#                 response.firstpageScore = '{:g}'.format(100 - fp_lost_score)
#         response.total = total
#         return response

#     def CheckProblem(self, request, context):
#         """质控问题详情
#         """
#         response = CheckProblemResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         problem = app.getProblemDetail(request.id)
#         unmarshalProblem(problem, response.data)
#         return response

#     def CheckEmr(self, request, context):
#         """检查文书是否存在质控问题
#         """
#         response = CheckEmrResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         req = {c: getattr(request, c) for c in ["caseId", "docId", "auditType"]}
#         problems, total = app.getCaseProblems(GetProblemListRequest(**req))
#         response.problemsExist = total > 0
#         return response

#     def AddCaseProblem(self, request, context):
#         """添加质控问题
#         """
#         response = CommonResponse()
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return

#         result = app.addCaseProblem(request.caseId, request.docId, request.qcItemId, request.operatorId,
#                                     request.operatorName,
#                                     request.doctor, request.comment, request.requirement, request.deductFlag,
#                                     request.score, request.counting, auditStep=request.auditStep)
#         response.isSuccess = result.isSuccess
#         response.message = result.message
#         return response

#     def UpdateCaseProblem(self, request, context):
#         """编辑质控问题
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = app.updateProblem(request.id, request.requirement, request.comment, request.deductFlag, request.score,
#                                    request.doctor, request.counting, request.operatorId, request.operatorName, auditStep=request.auditStep)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def DeleteCaseProblem(self, request, context):
#         """删除质控问题
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = app.deleteProblem(request.id, request.operatorId, request.operatorName, auditStep=request.auditStep)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def DeductProblem(self, request, context):
#         """设置扣分不扣分
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = app.deductProblem(request.id, request.deductFlag, request.operatorId, request.operatorName)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def GetCaseDoctors(self, request, context):
#         """获取病历的医生列表
#         """
#         response = GetCaseDoctorsResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         doctors = app.getCaseDoctors(
#             {'caseId': request.caseId, "input": request.input, 'attendingFlag': request.attendingFlag,
#              'department': request.department})
#         count = 0
#         if doctors:
#             for d in doctors:
#                 if count >= 50:
#                     break
#                 protoItem = response.doctors.add()
#                 protoItem.code = d.id
#                 protoItem.name = d.name or ""
#                 protoItem.department = d.department or ""
#                 protoItem.role = d.role or ""
#                 count += 1
#         response.total = count
#         return response

#     def GetRefuseDoctor(self, request, context):
#         """获取驳回医生
#         """
#         response = GetRefuseDoctorResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         refuseCode, fixDoctorFlag = app.getRefuseDoctor(request.caseId, request.docId)
#         response.doctor = refuseCode or ""
#         response.fixDoctorFlag = fixDoctorFlag
#         return response

#     def SetRefuseDoctor(self, request, context):
#         """设置驳回医生
#         """
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         result = app.setRefuseDoctor(request.caseId, request.docId, request.doctor, request.operatorId, request.operatorName)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def BatchSetRefuseDoctor(self, request, context):
#         """批量设置驳回医生
#         """
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         result = app.batchSetRefuseDoctor(request.problems, request.doctor, request.operatorId, request.operatorName)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def GetCaseReason(self, request, context):
#         """当前病历存在的问题说明
#         """
#         response = GetCaseReasonResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         problems = app.GetCaseReason(request.caseId, ignoreAi=request.ignoreAi, isAddRefuse=request.isAddRefuse)
#         emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000), withNoDocOption=True)
#         for emr in emrList:
#             protoItem = None
#             for p in problems:
#                 if p.docId == emr.docId:
#                     if not protoItem:
#                         protoItem = response.problems.add()
#                         protoItem.id = len(response.problems)
#                         protoItem.docId = p.docId
#                         protoItem.documentName = p.emrInfoModel.documentName if p.emrInfoModel else "缺失文书"
#                     reasonItem = protoItem.children.add()
#                     reasonItem.id = p.id
#                     reasonItem.reason = f'{p.reason}。{p.comment}'
#                     reasonItem.counting = p.getProblemCount()
#                     protoItem.count += p.getProblemCount()
#                     response.total += p.getProblemCount()
#         return response

#     def ApproveCase(self, request, context):
#         """归档
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = app.approve(request.caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def ApproveCaseBatch(self, request, context):
#         """批量归档
#         """
#         for caseId in request.caseId:
#             self.ApproveCase(
#                 CheckCaseRequest(caseId=caseId, operatorId=request.operatorId, operatorName=request.operatorName,
#                                  comment="", auditType=request.auditType, auditStep=request.auditStep), context)
#         return CommonResponse(isSuccess=True)

#     def RefuseCase(self, request, context):
#         """驳回
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = None
#         if request.transTo == 'audit':
#             # 终审不通过，退回给质控医生
#             result = app.recheckRefuse(request.caseId, request.operatorId, request.operatorName, request.comment)
#         elif request.transTo == 'clinic':
#             # 退回给临床医生
#             result = app.refuse(request, toClinic=True)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def RevokeApproved(self, request, context):
#         """撤销归档
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = None
#         # 撤销
#         result = app.cancelApprove(request.caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def RevokeRefused(self, request, context):
#         """撤销驳回
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = None
#         if request.transFrom == 'clinic':
#             # 从临床撤回
#             # TODO 查询驳回记录，emr接口需要的参数
#             result = app.cancelRefuse(request.caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep, transFrom=request.transFrom)
#         elif request.transFrom == 'audit':
#             # 从质控医生撤回
#             result = app.cancelRefuse(request.caseId, request.operatorId, request.operatorName, request.comment, toRecheck=True, auditStep=request.auditStep)
#             return CommonResponse(isSuccess=True)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def GetCaseCheckHistory(self, request, context):
#         """质控日志
#         """
#         response = GetCaseCheckHistoryResponse()
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         checkHistory, total = app.getCheckHistory(request.caseId, auditStep=request.auditStep,
#                                                   start=(request.page - 1) * request.count, size=request.count)
#         count = 0
#         for h in checkHistory:
#             protoItem = response.items.add()
#             unmarshalCheckHistory(h, protoItem)
#             count += 1
#         response.total = total
#         response.page = request.page
#         response.count = count
#         return response

#     def GetAdviceType(self, request, context):
#         """医嘱类别"""
#         response = GetAdviceTypeResponse()
#         with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
#             for o in self.context.getOrderTypeRepository("hospital").getList(session):
#                 protoItem = response.items.add()
#                 protoItem.code = o.type or ""
#                 protoItem.name = o.name or ""
#         return response

#     def GetMedicalAdvice(self, request, context):
#         """医嘱列表
#         """
#         response = GetMedicalAdviceResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         with app.app.mysqlConnection.session() as session:
#             listReq = {
#                 "caseId": request.caseId,
#                 "startTime": request.startTime,
#                 "endTime": request.endTime,
#                 "name": request.name,
#                 "start": (request.page - 1) * request.count,
#                 "size": request.count
#             }
#             if request.category:
#                 listReq["orderType"] = request.category.split(',')
#             if request.status:
#                 listReq["status"] = str(request.status).split(',')
#             if request.type:
#                 listReq["orderFlag"] = request.type.split(',')
#             req = GetOrderListRequest(**listReq)
#             orderList = self.context.getOrderRepository("hospital").search(session, req)
#             total = self.context.getOrderRepository("hospital").count(session, req)
#             drugTagDict = self.context.getOrderRepository("hospital").getDrugTags(session)
#             count = 0
#             for o in orderList:
#                 protoItem = response.items.add()
#                 unmarshalMedicalAdvice(o, protoItem)
#                 protoItem.tag = drugTagDict.get(protoItem.orderName, '')
#                 count += 1
#             response.total = total
#             return response

#     def GetCaseTimeline(self, request, context):
#         """病历审核流程
#         """
#         response = GetCaseTimelineResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(caseId=request.caseId)
#         if not caseInfo:
#             return response
#         audit = self.context.getAuditApplication("hospital").getAuditRecordById(caseInfo.audit_id)
#         for t in audit.getTimeline():
#             protoItem = response.data.add()
#             unmarshalAuditTimeline(t, protoItem)
#         return response

#     def GetRefusedProblem(self, request, context):
#         """驳回的问题清单
#         """
#         response = GetRefusedProblemResponse()
#         auditType = "hospital"
#         with self.context.getAuditApplication(auditType).app.mysqlConnection.session() as session:
#             audit = self.context.getAuditRepository(auditType).get(session, request.auditId)
#             if not audit:
#                 return
#             report = self.context.getRefuseHistoryRepository(auditType).getRefuseHistory(session, audit.caseId, request.time)
#             if not report:
#                 return
#             reportProblems = report.problems
#             response.time = report.refuse_time.strftime("%Y-%m-%d %H:%M") if report.refuse_time else ""
#             if isinstance(reportProblems, str):
#                 reportProblems = json.loads(reportProblems)
#             response.total = len(reportProblems)
#             # 医生列表
#             doctorCodes = [p.get("refuseCode", "") for p in reportProblems]
#             doctors = self.context.getDoctorRepository(auditType).getByCodes(session, doctorCodes)
#             emrList = self.context.getEmrRepository(auditType).getEmrList(session, GetEmrListRequest(caseId=audit.caseId, size=10000))
#             # 重新申请
#             applyDict = {}
#             refuseDetails = self.context.getRefuseHistoryRepository(auditType).getRefuseDetail(session, audit.caseId, report.id)
#             for d in refuseDetails:
#                 applyDict[d.doctor] = {
#                     "apply_flag": d.apply_flag or 0,
#                     "apply_time": d.apply_time.strftime("%Y-%m-%d %H:%M") if d.apply_time else "",
#                 }
#             doctorList = []

#             for d in doctors:
#                 if d.id in doctorList:
#                     continue
#                 protoItem = response.data.add()
#                 protoItem.doctor.name = d.name
#                 protoItem.doctor.department = d.department
#                 protoItem.doctor.code = d.id
#                 protoItem.applyStatus = applyDict.get(d.id).get("apply_flag", 0) if applyDict and applyDict.get(d.id) else 0
#                 protoItem.applyTime = applyDict.get(d.id).get("apply_time", "") if applyDict and applyDict.get(d.id) else ""
#                 for p in reportProblems:
#                     if p.get('refuseCode') == d.id:
#                         title = '缺失文书'
#                         for emr in emrList:
#                             if emr.docId == p.get('docId'):
#                                 title = emr.documentName
#                         problemItem = protoItem.problems.add()
#                         problemItem.docName = title
#                         problemItem.instruction = p.get('reason')
#                         problemItem.comment = p.get('comment')
#                         protoItem.count += 1
#         return response

#     def GetBranch(self, request, context):
#         """院区列表
#         """
#         response = GetBranchResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             for b in self.context.getBranchRepository("hospital").getList(session):
#                 response.branches.append(b.name)
#         return response

#     def GetWard(self, request, context):
#         """病区列表
#         """
#         response = GetWardResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             for w in self.context.getWardRepository("hospital").getList(session, name=request.name, branch=request.branch):
#                 protoItem = response.wards.add()
#                 protoItem.branch = w.branch or ""
#                 protoItem.name = w.name or ""
#             response.total = len(response.wards)
#         return response

#     def GetDepartment(self, request, context):
#         """科室列表
#         """
#         response = GetDepartmentResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             if request.mzFlag == 1:
#                 deptList = self.context.getDepartmentRepository("hospital").getMzList(session, request)
#                 response.departments.extend(deptList)
#             else:
#                 for d in self.context.getDepartmentRepository("hospital").getList(session, name=request.name, branch=request.branch):
#                     if not d.name:
#                         continue
#                     response.departments.append(d.name)
#             response.total = len(response.departments)
#         return response

#     def AddDepartment(self, request, context):
#         response = CommonResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             self.context.getDepartmentRepository("hospital").add(session, request.departments)
#         response.isSuccess = True
#         return response

#     def GetDiseaseList(self, request, context):
#         """专病诊断列表
#         """
#         response = GetDiseaseResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             for d in self.context.getDiseaseRepository("hospital").getList(session, sug=request.input):
#                 response.items.append(d.name)
#         return response

#     def GetDiagnosisList(self, request, context):
#         """诊断列表
#         """
#         response = GetDiagnosisResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             for d in self.context.getDiagnosisRepository("hospital").getList(session, sug=request.input):
#                 if d.code and d.name:
#                     protoItem = response.items.add()
#                     protoItem.code = d.code
#                     protoItem.name = d.name
#         return response

#     def GetOperationList(self, request, context):
#         """手术列表
#         """
#         response = GetOperationResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             for d in self.context.getOperationRepository("hospital").getList(session, sug=request.input):
#                 if d.code and d.name:
#                     protoItem = response.items.add()
#                     protoItem.code = d.code
#                     protoItem.name = d.name
#         return response

#     def GetCaseTag(self, request, context):
#         """病历标签
#         """
#         response = GetCaseTagResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         tags = app.getCaseTag(request.input)
#         for t in tags:
#             protoItem = response.data.add()
#             protoItem.id = t.id
#             protoItem.name = t.name or ""
#             protoItem.code = t.code or ""
#             protoItem.status = t.status or 0
#             protoItem.orderNo = t.orderNo or 0
#             protoItem.icon = t.icon or ""
#         return response

#     def GetAuditStatus(self, request, context):
#         """病历状态
#         """
#         response = GetAuditStatusResponse()
#         statusList = []
#         if request.auditStep == 'audit':
#             statusList = AUDIT_STATUS
#         elif request.auditStep == "recheck":
#             statusList = RECHECK_STATUS
#         for status in statusList:
#             if not status.get('hideflag'):
#                 protoItem = response.data.add()
#                 protoItem.id = status.get('returnid')
#                 protoItem.name = status.get('name')
#         return response

#     def GetReviewers(self, request, context):
#         """审核人列表
#         """
#         response = GetReviewersResponse()
#         if request.doctorType == 'assign':
#             for reviewer in self.context.getAuditApplication(request.auditType).getAssignedDoctors(request.input):
#                 if reviewer:
#                     response.doctors.append(reviewer)
#         elif request.doctorType == 'review':
#             for reviewer in self.context.getAuditApplication(request.auditType).getReviewers(request.input):
#                 if reviewer:
#                     response.doctors.append(reviewer)
#         response.total = len(response.doctors)
#         return response

#     def GetStandardEmr(self, request, context):
#         """标准文书列表
#         """
#         response = GetStandardEmrResponse()
#         with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
#             for name in self.context.getDocumentsRepository("hospital").getDistinctStandardName(session):
#                 if request.input:
#                     if request.input in name:
#                         response.items.append(name)
#                 elif name:
#                     response.items.append(name)
#             response.total = len(response.items)
#         return response

#     def GetCaseQcItems(self, request, context):
#         """病历可用的质控项列表
#         """
#         item_type_dict = {1: '通用', 2: '专科', 3: '专病'}
#         response = GetCaseQcItemsResponse()
#         if not request.page:
#             request.page = 1
#         if not request.count:
#             request.count = 50
#         app = self.context.getCaseApplication(request.auditType)
#         with app.app.mysqlConnection.session() as session:
#             case = app._caseRepository.getByCaseId(session, request.caseId)
#             department = case.outDeptName or case.department or ''
#             diagnosis = app.getDiagnosisInfo(session, request.caseId)
#             diagnosis_list = [d.name for d in diagnosis]
#             emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, docId=request.docId))
#             emrInfo = None
#             emrStandardName = "0"
#             for emr in emrList:
#                 emrInfo = emr
#             if emrInfo:
#                 document = self.context.getDocumentsRepository(request.auditType).get(session, emrInfo.getDocumentName())
#                 if not document:
#                     return response
#                 emrStandardName = document.standard_name
#             qcGroup = self.context.getQcGroupRepository(request.auditType).getQcGroup(session)
#             if not qcGroup:
#                 logging.info('没有找到规则组配置')
#                 return
#             index = 0
#             for item in self.context.getQcItemRepository("hospital").getList(session, GetItemsListRequest(emrName=emrStandardName, instruction=request.input, caseId=request.caseId, dept=department, diagnosis=diagnosis_list)):
#                 if item and qcGroup.getItem(item.id):
#                     if (request.page - 1) * request.count <= index < request.page * request.count:
#                         try:
#                             protoItem = response.items.add()
#                             protoItem.id = item.id or 0
#                             protoItem.code = item.code or ""
#                             protoItem.emrName = item.standard_emr or ""
#                             protoItem.requirement = item.requirement or ""
#                             protoItem.instruction = item.instruction or ""
#                             protoItem.typeName = item_type_dict.get(item.type, "")
#                             ruleItem = qcGroup.getItem(item.id)
#                             if ruleItem.score:
#                                 protoItem.score = '{:g}'.format(float(ruleItem.score))
#                                 protoItem.scoreValue = float(ruleItem.score)
#                         except Exception as e:
#                             print(e)
#                             continue
#                     index += 1
#             response.total = index
#         return response

#     def GetInpatientList(self, request, context):
#         """在院病历列表
#         """
#         response = GetInpatientListResponse()
#         return response

#     def GetCaseEmrList(self, request, context):
#         """文书列表
#         """
#         response = GetCaseEmrListResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return

#         emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000,
#                                                    documentName=request.documentName),
#                                  withNoDocOption=request.addSpec)
#         emrDict = {emr.docId: emr for emr in emrList}
#         emrCount = len(emrList) - 1 if request.addSpec else len(emrList)

#         # 文书编目录
#         catalog = app.getEmrCatalog(emrList)
#         emr_catalog = {}
#         catalogItems = []
#         groupItem = None
#         for c in catalog:
#             groupItem = response.catalog.add()
#             groupItem.cid = c.get('id') or 10000
#             groupItem.cname = c.get('name') or '其它'
#             groupItem.count = len(c.get('items', []))
#             for item in c.get('items', []):
#                 emr = emrDict.get(item)
#                 if not emr:
#                     continue
#                 protoItem = groupItem.list.add()
#                 protoItem.documentName = emr.documentName or ''
#                 protoItem.docId = emr.docId or ''
#                 protoItem.createTime = emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
#                 protoItem.isSave = emr.isSave or False
#                 protoItem.refuseDoctor = emr.getRefuseDoctor() or ''
#                 catalogItems.append(item)
#                 emr_catalog[emr.docId] = c
#         if len(catalogItems) < emrCount:
#             if not groupItem or groupItem.name != '其它':
#                 groupItem = response.catalog.add()
#                 groupItem.cid = 10000
#                 groupItem.cname = '其它'
#             for emr in emrList:
#                 if emr.docId in catalogItems:
#                     continue
#                 protoItem = groupItem.list.add()
#                 protoItem.docId = emr.docId or ''
#                 protoItem.documentName = emr.documentName or ''
#                 protoItem.createTime = emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
#                 protoItem.isSave = emr.isSave or False
#                 protoItem.refuseDoctor = emr.refuseCode or ''
#                 groupItem.count += 1
#         # 文书列表
#         if int(app.app.config.get(Config.QC_EMR_SORT) or 1) == 2:
#             emrList.sort(key=lambda data: data.recordTime if data.recordTime else data.createTime or datetime.now())
#         else:
#             emrList.sort(key=lambda data: emr_catalog.get(data.docId, {}).get('id', 10000))

#         # contentDocIdDict = app.countEmrContent(request.caseId)
#         emr_histories = app.getAuditEmrInfo(caseId=request.caseId)
#         total = 0
#         for emr in emrList:
#             protoItem = response.items.add()
#             unmarshalCaseEmr(emr, {}, protoItem)
#             # 文书目录
#             if emr.docId == '0':
#                 protoItem.catalogId = 0
#             else:
#                 protoItem.catalogId = emr_catalog.get(emr.docId).get('id')
#                 protoItem.catalog = emr_catalog.get(emr.docId).get('name')
#             # 文书的修改对应的申请记录，如果加上当前申请，多于1个版本说明有过修改
#             emr_audit = emr_histories.get(emr.docId, set())
#             # emr_audit.add(caseInfo.audit_id)
#             protoItem.isChange = 1 if len(emr_audit) > 1 else 0
#             total += 1
#         response.total = total
#         return response

#     def GetEmrVersion(self, request, context):
#         """emr版本
#         """
#         response = GetEmrVersionResponse()
#         app = self.context.getAuditApplication("hospital")
#         if not app:
#             return

#         # 查询文书的修改记录
#         versions = app.getEmrVersions(caseId=request.caseId, docId=request.docId)
#         for version in versions:
#             protoItem = response.data.add()
#             protoItem.auditId = str(version.audit_record.id)
#             protoItem.version = str(version.dataId)
#             protoItem.applyTime = version.audit_record.applyTime.strftime("%Y-%m-%d %H:%M") if version.audit_record.applyTime else ""
#             protoItem.updateTime = version.createTime.strftime("%Y-%m-%d %H:%M") if version.createTime else ""
#             req = {'auditId': str(version.audit_record.id), 'caseId': request.caseId, 'docId': request.docId, 'auditType': request.auditType}
#             problems, total = self.context.getCaseApplication('hospital').getCaseProblems(GetProblemListRequest(**req))
#             protoItem.problemCount = total
#         return response

#     def GetEmrDiff(self, request, context):
#         """历史版本文书和当前版本对比
#         """
#         response = GetEmrDiffResponse()
#         response.caseId = request.caseId
#         response.docId = request.docId
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         audit = self.context.getAuditApplication("hospital").getAuditRecordById(auditId=request.auditId)
#         if not audit:
#             return
#         version_now = app.getEmrVersionByAudit(request.caseId, request.docId, caseInfo.audit_id)
#         version_old = app.getEmrVersionByAudit(request.caseId, request.docId, request.auditId)
#         response.diff = self.context.getEmrRepository("hospital").diff(old=version_old, new=version_now)
#         response.newVersion = version_now.getMd5()
#         response.oldVersion = version_old.getMd5()
#         response.title = f"【{version_now.getDocumentName()}】{audit.applyTime.strftime('%Y-%m-%d')}申请版本同当前最新版本对比结果"
#         # response.title = f"【{version_now.getDocumentName()}】历史申请版本同当前最新版本对比结果"
#         for title, version in {'最新版本问题': version_now, "{applyTime}版本问题".format(applyTime=audit.applyTime.strftime('%Y-%m-%d')): version_old}.items():
#         # for title, version in {'最新版本问题': version_now, "历史版本问题": version_old}.items():
#             item = response.problems.add()
#             req = {'caseId': request.caseId, 'docId': request.docId, 'auditType': request.auditType}
#             if title == '最新版本问题':
#                 req['auditId'] = caseInfo.audit_id
#             else:
#                 req['auditId'] = request.auditId
#             version_problems, total = self.context.getCaseApplication('hospital').getCaseProblems(GetProblemListRequest(**req))
#             unmarshalDiffProblem(item, version_problems, total, title)
#         return response

#     def GetCaseEmr(self, request, context):
#         """文书内容
#         """
#         response = GetCaseEmrResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, docId=request.emrId, withContent=True))
#         for emr in emrList:
#             unmarshalCaseEmr(emr, {emr.getEmrContentId(): emr.getEmrHtml()}, response.data)
#         return response

#     def AddQCItemProblem(self, request, context):
#         """添加质控点和问题
#         """
#         response = CommonResponse()
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         result = app.addCaseProblem(request.caseId, request.docId, qcItemId=0, operatorId=request.operatorId, operatorName=request.operatorName,
#                                     refuseDoctor=request.doctor, comment=request.comment, requirement=request.requirement,
#                                     deductFlag=request.deductFlag, score=request.score, count=request.counting,
#                                     newQcItemFlag=True, auditStep=request.auditStep, categoryId=request.categoryId)
#         response.isSuccess = result.isSuccess
#         response.message = result.message
#         return response

#     def GetConfigItems(self, request, context):
#         """配置项
#         """
#         response = GetConfigItemsResponse()
#         app = self.context.getAuditApplication("hospital")
#         if not app:
#             return
#         configItems = app.app.config.itemList
#         for item in configItems:
#             protoItem = response.items.add()
#             protoItem.name = item.name
#             protoItem.value = str(item.value) if item.value else ""
#             protoItem.system = item.platform if item.platform else ""
#             protoItem.scope = item.scope if item.scope else ""

#         return response

#     def CaseExport(self, request, context):
#         """
#         病例导出excel
#         """
#         response = GetCaseExportResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         # 查询用户数据权限
#         field, pList = app.getDeptPermission(request.operatorId)
#         logging.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')
#         have_sample = 2
#         if request.auditType != AUDIT_TYPE_ACTIVE:
#             have_sample = int(app.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=request.auditType), 2))
#         group_flag = int(app.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)

#         req = self.get_case_list_req(app, request, is_export=1, field=field, p_list=pList)
#         caseList, total = app.getCaseList(req)
#         operation_data, diagnosis_data = {}, {}
#         if request.auditType == AUDIT_TYPE_ACTIVE:
#             caseIds = [item.caseId for item in caseList]
#             operation_data = app.getCaseOperationData(caseIds)
#             diagnosis_data = app.getCaseDiagnosis(caseIds, isMz=True)
#         patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME)
#         base_file_name = EXPORT_FILE_AUDIT_TYPE.get(request.auditType) + EXPORT_FILE_AUDIT_STEP.get(request.auditStep) + "-{}.xlsx"
#         file_name = base_file_name.format(datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(10, 99)))
#         file_id = uuid.uuid4().hex
#         path_file_name = self.export_path + file_id + ".xlsx"
#         # sort_field = 'dischargeTime' if request.auditType != AUDIT_TYPE_ACTIVE else 'admitTime'
#         # sortBy = [(sort_field, -1)]
#         # if request.sortField:
#         #     sortBy = [(item.field, SORT_DESC_DICT.get(item.way.upper(), -1)) for item in request.sortField]

#         # 事中质控根据配置项决定导出是否包含重点病历列
#         tag_hide = app.app.config.get(Config.QC_ACTIVE_TAGS) == '2' and request.auditType == AUDIT_TYPE_ACTIVE
#         data, data_yaml, reason_column = app.format_qc_list_export_data(caseList, request, have_sample, patient_id_name, group_flag=group_flag, operation_data=operation_data, diagnosis_data=diagnosis_data, tag_hide=tag_hide)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, data)
#         column_width = []
#         if request.detailFields.problem and reason_column:
#             column_width = [reason_column, 120]
#         processor.toExcel(path=path_file_name, column_width=column_width)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def DownloadFile(self, request, context):
#         """
#         已导出病例下载
#         """
#         response = DownloadFileResponse()
#         if not request.id:
#             raise Exception("DownloadFile require id")
#         filename = request.id + ".xlsx"
#         fullname = os.path.join(self.export_path, filename)
#         if not os.path.exists(fullname):
#             filename = request.id + ".xls"
#             fullname = os.path.join(self.export_path, filename)
#         with open(fullname, "rb") as f:
#             response.file = f.read()
#         return response

#     def CrawlCase(self, request, context):
#         """手动请求更新病历数据
#         """
#         response = CommonResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         if caseInfo.getCaseType() == CaseType.SNAPSHOT:
#             originCaseInfo = app.getCaseDetail(caseInfo.originCaseId)
#             if not originCaseInfo:
#                 return
#             if originCaseInfo.dischargeTime:
#                 response.message = "当前患者已出院，不可更新病历！"
#                 return response
#             sampleApp = self.context.getSampleApplication(request.auditType)
#             if not sampleApp:
#                 return
#             response.isSuccess = sampleApp.sendSnapshotMessage([request.caseId], request.auditType)
#         else:
#             auditApp = self.context.getAuditApplication(request.auditType)
#             if not auditApp:
#                 return
#             response.isSuccess = auditApp.crawlCase(caseInfo.caseId, caseInfo.patientId, auditType=request.auditType)
#         return response

#     def GetCaseDeductDetail(self, request, context):
#         """
#         院级病案得分扣分明细接口的默认实现
#         """
#         response = GetCaseDeductDetailResponse()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000))
#         emrDict = {emr.docId: emr.documentName for emr in emrList}
#         emrDict['0'] = "缺失文书"

#         app = self.context.getAuditApplication('hospital')
#         if not app:
#             return
#         deductList = app.getDeductDetail(caseInfo.caseId, caseInfo.audit_id)
#         for item in deductList:
#             data = response.data.add()
#             data.instruction = item.reason
#             data.totalScore = item.score
#             data.documentName = emrDict.get(item.docId, "") or ''
#             data.docId = item.docId or ''
#             data.createTime = item.createTime or ''
#             data.operatorName = item.operatorName or ''
#             data.problemCount = item.problemCount or 0
#             data.singleScore = item.singleScore or 0
#             data.qcItemId = item.qcItemId or 0
#         response.total = len(deductList)
#         return response

#     def GetQCReport(self, request, context):
#         """质控评分表
#         """
#         response = GetQCReportResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         response.patientId = caseInfo.inpNo or caseInfo.patientId
#         response.name = caseInfo.name

#         report = app.getScoreReport(request.caseId)
#         response.content = report
#         return response

#     def GetEmrData(self, request, context):
#         """获取病历数据用于质控 - ai质控专用
#         """
#         response = GetEmrDataResponse()
#         # 病历基本信息
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         # 赋值基本信息
#         response.basicInfo.id = caseInfo.id or 0
#         response.basicInfo.caseId = caseInfo.caseId or ""
#         response.basicInfo.patientId = caseInfo.patientId or ""
#         response.basicInfo.visitTimes = caseInfo.visitTimes or 0
#         response.basicInfo.name = caseInfo.name or ""
#         response.basicInfo.gender = parseGender(caseInfo.gender)
#         response.basicInfo.age = f'{caseInfo.age or ""}{caseInfo.ageUnit or ""}'
#         response.basicInfo.hospital = caseInfo.hospital or ""
#         response.basicInfo.branch = caseInfo.branch or ""
#         response.basicInfo.department = caseInfo.department or ""
#         response.basicInfo.attendDoctor = caseInfo.attendDoctor or ""
#         response.basicInfo.admitTime = caseInfo.admitTime.strftime('%Y-%m-%d %H:%M:%S') if caseInfo.admitTime else ""
#         response.basicInfo.dischargeTime = caseInfo.dischargeTime.strftime('%Y-%m-%d %H:%M:%S') if caseInfo.dischargeTime else ""
#         if caseInfo.dischargeTime:
#             response.basicInfo.inpDays = caseInfo.inpDays or 0
#         response.basicInfo.isDead = True if caseInfo.isDead else False
#         response.basicInfo.diagnosis = caseInfo.diagnosis or ""
#         response.basicInfo.ward = caseInfo.wardName or ""
#         response.basicInfo.bedno = caseInfo.bedId or ""
#         response.basicInfo.dischargeDept = caseInfo.outDeptName or ""
#         # TODO 将标准文书对照加入到getCaseEmr中，一次查询获取到类型对应的文书列表
#         for emr in app.getAIEmrData(request.caseId, request.docType):
#             protoItem = response.emr.add()
#             unmarshalCaseEmr(emr, {emr.getEmrContentId(): emr.getEmrHtml()}, protoItem, {emr.getEmrContentId(): emr.getEmrContents()})
#             if protoItem.createTime == "":
#                 protoItem.createTime = '0001-01-01 00:00:00'
#             if protoItem.updateTime == "":
#                 protoItem.updateTime = '0001-01-01 00:00:00'
#             if protoItem.recordTime == "":
#                 protoItem.recordTime = '0001-01-01 00:00:00'
#         # 医嘱
#         if not request.docType or '医嘱' in request.docType:
#             for order in app.getMedicalAdvice(GetOrderListRequest(caseId=request.caseId, size=10000)):
#                 protoItem = response.doctor_advice.add()
#                 protoItem.order_no = order.order_no or ''
#                 protoItem.order_type = order.order_type or ''
#                 protoItem.set_no = order.set_no or ''
#                 protoItem.date_start = order.date_start.strftime('%Y-%m-%d %H:%M:%S') if order.date_start else ''
#                 protoItem.date_stop = order.date_stop.strftime('%Y-%m-%d %H:%M:%S') if order.date_stop else ''
#                 protoItem.code = order.code or ''
#                 protoItem.name = order.name or ''
#                 protoItem.dosage = order.dosage or ''
#                 protoItem.unit = order.unit or ''
#                 protoItem.instruct_name = order.instruct_name or ''
#                 protoItem.frequency_code = order.frequency_code or ''
#                 protoItem.frequency_name = order.frequency_name or ''
#                 protoItem.order_flag = order.order_flag or ''
#         return response

#     def ArchiveScoreExport(self, request, context):
#         """院级病历得分病历列表导出
#         """
#         response = GetCaseExportResponse()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         params = ["branch", "ward", "department", "attend", "rating",
#                   "caseId", "patientId", "reviewer", "problemFlag", "patientName",
#                   "autoReviewFlag", "firstPageFlag", "start", "size",
#                   "auditType", "auditStep", "startTime", "endTime", "caseType", "deptType", "timeType",
#                   "diagnosis", "operation", "archiveRating", "refuseCount"]
#         req = {c: getattr(request, c) for c in params}
#         req["is_export"] = 1
#         if request.caseType:
#             if request.caseType == 'running':
#                 req['includeCaseTypes'] = [CaseType.ACTIVE]
#             elif request.caseType == 'archived':
#                 req['includeCaseTypes'] = [CaseType.ARCHIVE]
#             elif request.caseType == 'Final':
#                 req['includeCaseTypes'] = [CaseType.FINAL]
#         req['isFinal'] = request.auditStep == "recheck"
#         if request.assignDoctor:
#             req['sampleExpert'] = request.assignDoctor
#         if app.app.config.get(Config.QC_PRECONDITION.format(auditType=request.auditType)):
#             req["precondition"] = app.app.config.get(Config.QC_PRECONDITION.format(auditType=request.auditType))
#         req["not_apply"] = app.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType=request.auditType))
#         if request.tag:
#             req['tags'] = [request.tag]
#         req['timeType'] = int(request.timeType) if request.timeType else 0
#         req = GetCaseListRequest(**req)

#         caseList, total = app.getCaseList(req)

#         workbook = openpyxl.Workbook()
#         sheet = workbook.active
#         patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME)
#         app.writeArchiveScoreExcel(sheet, caseList, patient_id_name)

#         file_id = uuid.uuid4().hex
#         workbook.save(self.export_path + file_id + ".xlsx")

#         response.id = file_id
#         now = arrow.utcnow().to('+08:00').naive.strftime("%Y%m%d")
#         response.fileName = f'院级病案得分统计-{now}.xlsx'
#         return response

#     def AddRefuseCase(self, request, context):
#         """
#         追加退回
#         :return:
#         """
#         app = self.context.getAuditApplication(request.auditType)
#         result = app.refuse(request, toClinic=True, isAdd=True)
#         return CommonResponse(isSuccess=result.isSuccess, message=result.message)

#     def GetCaseLab(self, request, context):
#         """化验报告
#         """
#         response = GetCaseLabResponse()
#         app = self.context.getCaseApplication('hospital')
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         response.caseId = caseInfo.caseId
#         reports, total = app.getCaseLabList(GetLabListRequest(caseId=request.caseId, start=request.start, size=request.size or 100))
#         for r in reports:
#             protoItem = response.data.add()
#             unmarshalLabReport(r, protoItem)
#         response.total = total
#         return response

#     def GetCaseExam(self, request, context):
#         """检查报告
#         """
#         response = GetCaseExamResponse()
#         app = self.context.getCaseApplication('hospital')
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         response.caseId = caseInfo.caseId
#         reports, total = app.getCaseExamList(GetExamListRequest(caseId=request.caseId, withTotal=True, start=request.start, size=request.size or 100))
#         for exam in reports:
#             protoItem = response.data.add()
#             unmarshalExamination(exam, protoItem)
#         response.total = total
#         return response

#     def GetCalendar(self, request, context):
#         """获取日历维护数据
#         """
#         return self.calendarSvc.GetCalendar(request, context)

#     def SetCalendar(self, request, context):
#         """设置日历信息
#         """
#         return self.calendarSvc.SetCalendar(request, context)

#     def GetIpBlockList(self, request, context):
#         """获取医生端ip黑白名单列表
#         """
#         return self.ipBlockSvc.GetIpBlockList(request, context)

#     def UpdateIpBlock(self, request, context):
#         """创建或更新黑名单
#         """
#         return self.ipBlockSvc.UpdateIpBlock(request, context)

#     def DeleteIpBlock(self, request, context):
#         """删除ip黑白名单
#         """
#         return self.ipBlockSvc.DeleteIpBlock(request, context)

#     def SetConfigItems(self, request, context):
#         """设置配置项
#         """
#         """配置项
#         """
#         response = CommonResponse()
#         app = self.context.getAuditApplication("hospital")
#         if not app:
#             return
#         app.app.config.set(request.name, request.value, platform=request.system, scope=request.scope)
#         response.isSuccess = True
#         return response

#     def GetConfigList(self, request, context):
#         response = GetConfigListResponse()
#         app = self.context.getAuditApplication('hospital')
#         items = app.app.config.getConfigList(request)
#         for item in items:
#             protoItem = response.items.add()
#             protoItem.scope = item.scope or ''
#             protoItem.name = item.name_ch or ''
#             protoItem.value = item.value or ''
#             protoItem.description = item.message or ''
#             protoItem.type = item.type or ''
#             protoItem.key = item.name or ''
#             protoItem.default = item.default_value or ''
#             if item.choice:
#                 for i in item.choice.split('|'):
#                     s = Struct()
#                     s.update(json.loads(i))
#                     protoItem.choice.append(s)
#         return response

#     def UpdateConfigList(self, request, context):
#         response = CommonResponse()
#         app = self.context.getAuditApplication('hospital')
#         app.updateConfig(request)
#         app.app.config.reload()
#         response.isSuccess = True
#         return response

#     def CaseGroupList(self, request, context):
#         """
#         诊疗组筛选框列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CaseGroupListResponse()
#         app = self.context.getAuditApplication('hospital')
#         app.getGroupList(request.input, response)
#         return response

#     def ArchiveSampleList(self, request, context):
#         """抽取病历列表查询结果直接归档
#         """
#         response = CommonResponse()
#         app = self.context.getAuditApplication(request.auditType)
#         if not app:
#             return
#         if app.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=request.auditType)) != '1':
#             return response
#         field, pList = app.getDeptPermission(request.operatorId)
#         req = self.get_case_list_req(app, request, field=field, p_list=pList)
#         existCaseIds = list(request.existCaseIds) if request.existCaseIds else []
#         req.start = 0
#         req.size = 1000000
#         result = app.archiveCaseList(req, request.operatorId, exclude=existCaseIds)
#         response.isSuccess = result.isSuccess
#         response.message = result.message

#         # 异步处理归档
#         self._check_archive_task()
#         return response

#     def ExternalSystemLinks(self, request, context):
#         """获取其它系统的外链
#         """
#         response = ExternalSystemLinksResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         doctorId = request.operatorName
#         caseInfo = app.getCaseDetail(request.caseId)
#         for link in app.getExternalLinks():
#             protoItem = response.links.add()
#             protoItem.title = link.title
#             protoItem.url = link.url
#             protoItem.icon = link.icon or ""
#             if caseInfo:
#                 protoItem.url = link.url.format(caseId=caseInfo.caseId, patientId=caseInfo.patientId, inpNo=caseInfo.inpNo, doctorId=doctorId)
#         return response

#     def ActiveSave(self, request, context):
#         """
#         事中质控-保存质控结果
#         :return:
#         """
#         response = CommonResponse()
#         app = self.context.getCaseApplication(request.auditType)
#         if not app:
#             return
#         operatorId, name, operatorName = self.context.getAuditApplication(request.auditType).ensureUserName(request.operatorId, request.operatorName)
#         app.active_save(request, name)
#         response.isSuccess = True
#         return response

#     def ProblemRecordList(self, request, context):
#         """
#         问题日志列表
#         :return:
#         """
#         response = ProblemRecordListResponse()
#         app = self.context.getCaseApplication("hospital")
#         data, response.total = app.getProblemRecordList(request)
#         for item in data:
#             protoItem = response.data.add()
#             unmarshalProblemRecordList(protoItem, item)
#         return response

#     def ProblemRecordDetail(self, request, context):
#         """
#         问题日志详情
#         :return:
#         """
#         response = ProblemRecordDetailResponse()
#         app = self.context.getCaseApplication("hospital")
#         data = app.getProblemRecordDetail(request)
#         for item in data:
#             protoItem = response.data.add()
#             unmarshalProblemRecordDetail(protoItem, item)
#         return response

#     def UrgeRefusedCase(self, request, context):
#         """针对已退回状态的病历，在配置项可选的环节 对科室质控催办
#         """
#         response = CommonBatchResponse()
#         app = self.context.getCaseApplication("hospital")
#         if not app:
#             return
#         app.urgeRefusedCase(request.caseIds)
#         response.isSuccess = True
#         return response
