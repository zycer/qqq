# #!/usr/bin/env python
# # -*- coding:utf-8 -*-
# """
# @Author: zhangda@rxthinking.com
# @file: doctor_service.py
# @time: 2021/7/22 7:27 下午
# @desc:
# """
# import logging

# from iyoudoctor.hosp.qc.v3.doctor import GetDoctorIsRemindResponse, CommonResponse, GetDoctorRefuseCaseNumResponse, \
#     GetDoctorRefuseCaseListResponse, GetDoctorEMRProblemNumResponse, GetDoctorEMRProblemListResponse, \
#     GetDoctorEMRAuditRecordListResponse, GetEMRCaseSubmitApplyListResponse, GetDoctorEMRExtractProblemListResponse, \
#     GetCaseStatusResponse, GetAppealNotReadCountResponse, GetAppealNotReadCaseListResponse, GetCaseAppealDetailResponse, \
#     GetDoctorCaseListResponse, GetIpPlanResponse, TryCancelApplyArchiveResponse
# from iyoudoctor.hosp.qc.v3.doctor.service_pb2_grpc_wrapper import DoctorMatterManagerServicer
# from iyoudoctor.hosp.v2.qc import GetCaseAppealProblemListResponse

# from qcaudit.common.const import AUDIT_TYPE_HOSPITAL
# from qcaudit.config import Config
# from qcaudit.domain.doctor.appeal_repository import AppealRepository
# from qcaudit.domain.doctor.apply_archive_req import ApplyArchiveRequest
# from qcaudit.domain.doctor.doctor_repository import DoctorRepository

# from iyoudoctor.internals.framework import Invocation
# from iyouframework.grpc.utils import getFirstMetadataValue


# class DoctorService(DoctorMatterManagerServicer):
#     """
#     医生端接口服务类
#     """

#     def __init__(self, context):
#         self.context = context
#         self.doctor_repository = DoctorRepository(self.context.app, AUDIT_TYPE_HOSPITAL)
#         self.appeal_repository = AppealRepository(self.context.app, AUDIT_TYPE_HOSPITAL)

#     def GetDoctorIsRemind(self, request, context):
#         """
#         查询当前医生是否需要提醒
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorIsRemindResponse()
#         is_remind, doctor_name = self.doctor_repository.query_doctor_is_remind(request.doctor)
#         response.isRemind = is_remind
#         response.doctorName = doctor_name
#         return response

#     def UpdateDoctorNotRemind(self, request, context):
#         """
#         更新当前医生今日不再提醒
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         notRemind = request.notRemind or 0
#         if notRemind == 1:
#             self.doctor_repository.update_doctor_not_remind(request.doctor, notRemind)
#         response.isSuccess = True
#         return response

#     def GetDoctorRefuseCaseNum(self, request, context):
#         """
#         查询当前医生待整改病历数量
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorRefuseCaseNumResponse()
#         total, firstNum, secondNum, thirdNum, doctorName = self.doctor_repository.query_doctor_refuse_num(request.doctor)
#         response.total = total
#         response.firstNum = firstNum
#         response.secondNum = secondNum
#         response.thirdNum = thirdNum
#         return response

#     def GetDoctorRefuseCaseList(self, request, context):
#         """
#         获取当前医生待办病历列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorRefuseCaseListResponse()
#         doctor = request.doctor
#         with self.context.app.mysqlConnection.session() as session:
#             waitAlterCaseCount = self.doctor_repository.query_wait_alter_case_list(session, doctor, response)
#             patientType = self.context.app.config.get(Config.QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE, None)
#             onlineStartTime = self.context.app.config.get(Config.QC_FIRST_ONLINE_PUBLISH_TIMESTAMP, None)
#             waitApplyCaseCount = self.doctor_repository.query_wait_apply_case_list(session, doctor, response, patientType, onlineStartTime)
#             extractCaseCount, extractNotReadCaseCount = self.doctor_repository.query_extract_case_list(session, doctor,
#                                                                                                        response)
#             threeDayStartTime, twoDayStartTime = self.doctor_repository.query_three_day_start_time(session)

#             response.threeDayStartTime = threeDayStartTime
#             response.twoDayStartTime = twoDayStartTime
#             response.waitAlterCaseCount = waitAlterCaseCount
#             response.waitApplyCaseCount = waitApplyCaseCount
#             response.extractCaseCount = extractCaseCount
#             response.extractNotReadCaseCount = extractNotReadCaseCount

#         return response

#     def GetDoctorEMRProblemNum(self, request, context):
#         """
#         获取emr文书外框架问题数
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorEMRProblemNumResponse()
#         caseId = request.caseId or ""
#         if not caseId:
#             # 前端需求，仅传doctorId时为查询医生待整改病历数
#             total, firstNum, secondNum, thirdNum, doctorName = self.doctor_repository.query_doctor_refuse_num(
#                 request.doctor)
#             response.problemCount = total
#             response.doctorName = doctorName
#             return response
#         problemCount, doctorName = self.doctor_repository.query_emr_problem_count(request)

#         response.problemCount = problemCount
#         response.doctorName = doctorName
#         return response

#     def GetDoctorEMRProblemList(self, request, context):
#         """
#         获取emr文书问题列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorEMRProblemListResponse()
#         auditId = request.auditId or 0
#         refuseTime = request.refuseTime or ""
#         if auditId and refuseTime:
#             self.doctor_repository.query_emr_assign_audit_record_problem_list(request, response)
#         else:
#             self.doctor_repository.query_emr_problem_list(request, response)
#         return response

#     def GetDoctorEMRAuditRecordList(self, request, context):
#         """
#         获取emr文书质控流程列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorEMRAuditRecordListResponse()
#         self.doctor_repository.query_emr_audit_record(request, response)
#         return response

#     def UpdateProblemFixFlag(self, request, context):
#         """
#         问题整改完成
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.update_problem_fix(request, response)
#         return response

#     def ProblemAppeal(self, request, context):
#         """
#         问题申诉
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.update_problem_appeal(request, response)
#         return response

#     def ProblemIgnore(self, request, context):
#         """
#         问题忽略
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.update_problem_ignore(request, response)
#         return response

#     def GetEMRCaseSubmitApplyList(self, request, context):
#         """
#         emr提交病历申请列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetEMRCaseSubmitApplyListResponse()
#         if not request.caseIds:
#             return response
#         doctor_veto = self.context.app.config.get(Config.QC_DOCTOR_VETO, 1) == 2
#         self.doctor_repository.query_submit_apply_case_list(request, response, doctor_veto)
#         return response

#     def EMRCaseSubmit(self, request, context):
#         """
#         emr病历外提交
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.case_submit(request, response)
#         return response

#     def EMRDocSave(self, request, context):
#         """
#         emr文书保存
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.emr_doc_save(request, response)
#         return response

#     def EMRDocPartSave(self, request, context):
#         """
#         emr文书部分保存
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.emr_doc_part_save(request, response)
#         return response

#     def EMRDocDelete(self, request, context):
#         """
#         emr文书删除
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         self.doctor_repository.emr_doc_delete(request, response)
#         return response

#     def GetDoctorEMRExtractProblemList(self, request, context):
#         """
#         获取emr文书抽检问题列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorEMRExtractProblemListResponse()
#         self.doctor_repository.query_emr_extract_problem_list(request, response)
#         return response

#     def UpdateCaseIsRead(self, request, context):
#         """
#         更新抽检病历已读
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         if not request.caseIds:
#             response.message = "无caseId信息"
#             response.isSuccess = False
#             return response
#         self.doctor_repository.update_extract_case_is_read(request, response)
#         return response

#     def GetCaseStatus(self, request, context):
#         """
#         获取病历状态
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetCaseStatusResponse()
#         response.caseId = request.caseId
#         response.status = self.doctor_repository.get_case_status(request.caseId)
#         return response

#     def GetAppealNotReadCount(self, request, context):
#         """
#         当前医生查询未读申诉消息个数
#         """
#         response = GetAppealNotReadCountResponse()
#         self.appeal_repository.query_not_read_count(request, response)
#         return response

#     def GetAppealNotReadCaseList(self, request, context):
#         """
#         当前医生查询未读申诉消息病历列表
#         """
#         response = GetAppealNotReadCaseListResponse()
#         self.appeal_repository.get_not_read_case_list(request, response)
#         return response

#     def GetCaseAppealProblemList(self, request, context):
#         """
#         申诉病历问题列表
#         """
#         response = GetCaseAppealProblemListResponse()
#         self.appeal_repository.get_problem_list(request, response)
#         return response

#     def GetCaseAppealDetail(self, request, context):
#         """
#         病历问题申诉详情
#         """
#         response = GetCaseAppealDetailResponse()
#         self.appeal_repository.get_appeal_detail(request, response)
#         return response

#     def AppealCreate(self, request, context):
#         """
#         申诉创建
#         """
#         response = CommonResponse()
#         self.appeal_repository.create(request, response)
#         return response

#     def AppealDelete(self, request, context):
#         """
#         申诉删除
#         """
#         response = CommonResponse()
#         self.appeal_repository.delete(request, response)
#         return response

#     def AppealProblemIsRead(self, request, context):
#         """
#         更新申诉信息已读
#         """
#         response = CommonResponse()
#         self.appeal_repository.update_read(request, response)
#         return response

#     def AppealModify(self, request, context):
#         """
#         申诉修改
#         """
#         response = CommonResponse()
#         self.appeal_repository.modify(request, response)
#         return response

#     def EMRCaseTransfer(self, request, context):
#         """
#         emr病历转科
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonResponse()
#         # todo emr给转科接口
#         response.isSuccess = True
#         return response

#     def MessageReceive(self, request, context):
#         response = CommonResponse()
#         find_func = {
#             1: self.doctor_repository.send_create_msg,
#         }
#         if request.messageType not in find_func:
#             response.isSuccess = False
#             response.message = '消息类型不存在'
#             return response
#         find_func[request.messageType](request)
#         response.isSuccess = True
#         return response

#     def EmrSaveDebug(self, request, context):
#         """
#         医生端debug，记录日志
#         """
#         response = CommonResponse()
#         self.doctor_repository.logDebug(request, response)
#         return response

#     def GetIpPlan(self, request, context):
#         """
#         IP黑名单接口
#         """
#         response = GetIpPlanResponse()
#         # grpc metadata 中没有 x-real-ip 只有 x-forwarded-for
#         logging.info(context.invocation_metadata())
#         client_ip = getFirstMetadataValue(context, "x-forwarded-for").split(',')[0].strip()
#         logging.info(f"GetIpPlan: content.x-forwarded-for = [{client_ip}]")

#         # 根据配置项获取医生端插件开关，医生端开=>只有黑名单不显示，医生端关=>只有白名单显示
#         doctor_switch = self.context.app.config.get(Config.QC_DOCTOR_SWITCH, None)
#         if not doctor_switch or doctor_switch == "on":
#             response.socketType = self.doctor_repository.get_ip_rule(client_ip)
#         else:
#             response.socketType = 1
#             if self.doctor_repository.get_ip_rule(client_ip) == 2:
#                 response.socketType = 2
#         return response

#     def ApplyArchive(self, request, context):
#         """申请归档
#         """
#         response = CommonResponse()
#         self.doctor_repository.case_submit(ApplyArchiveRequest(caseIds=[request.caseId], doctor=request.doctor), response)
#         return response

#     def TryCancelApplyArchive(self, request, context):
#         """查询是否可以撤销申请归档
#         """
#         response = TryCancelApplyArchiveResponse()
#         caseInfo = self.context.getCaseApplication("hospital").getCaseDetail(caseId=request.caseId)
#         if not caseInfo:
#             response.message = "病历号未找到"
#             return response
#         audit = self.context.getAuditApplication("hospital").getAuditRecordById(caseInfo.audit_id)
#         response.caseId = request.caseId
#         response.permitted = not audit.isOperated()
#         return response
