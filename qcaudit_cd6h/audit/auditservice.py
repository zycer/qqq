# #!/usr/bin/env python3
# import uuid
# import openpyxl
# import arrow

# from qcaudit.config import Config
# from qcaudit.domain.case.case import CaseType
# from qcaudit.domain.case.req import GetEmrListRequest, GetCaseListRequest
# from qcaudit.service.auditservice import AuditService as _AuditService
# from iyoudoctor.hosp.qc.v3.qcaudit.service_message_pb2 import GetCaseDeductDetailResponse, GetCaseExportResponse


# class AuditService(_AuditService):

#     # TODO 把扣分明细默认接口逻辑添加到标准版本里
#     def GetCaseDeductDetail(self, request, context):
#         """扣分明细
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
