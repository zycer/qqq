from . import *
from qcaudit.env_config.pre_req import *
from qcaudit.common.const import *
from .qc_util import QCUtil
from qcaudit.service.protomarshaler import *
from qcaudit.config import Config
from qcaudit.domain.doctor.apply_archive_req import ApplyArchiveRequest


class GetDoctorIsRemind(MyResource):

    @pre_request(request, ["doctor"])
    def get(self):
        """
        查询当前医生是否需要提醒
        :return:
        """
        response = {}
        response["isRemind"], response["doctorName"] = doctor_repository.query_doctor_is_remind(request.doctor)
        return response


class UpdateDoctorNotRemind(MyResource):

    @pre_request(request, ["doctor", "notRemind:int"])
    def post(self):
        """
        更新当前医生今日不再提醒
        """
        notRemind = request.notRemind or 0
        if notRemind == 1:
            doctor_repository.update_doctor_not_remind(request.doctor, notRemind)
        return g.result


class GetDoctorRefuseCaseNum(MyResource):

    @pre_request(request, ["doctor"])
    def get(self):
        """
        查询当前医生待整改病历数量
        :param request:
        :param context:
        :return:
        """
        response = {}
        total, firstNum, secondNum, thirdNum, doctorName = doctor_repository.query_doctor_refuse_num(request.doctor)
        response["total"] = total
        response["firstNum"] = firstNum
        response["secondNum"] = secondNum
        response["thirdNum"] = thirdNum
        return response


class GetDoctorRefuseCaseList(MyResource):

    @pre_request(request, ["doctor"])
    def get(self):
        """
        获取当前医生待办病历列表
        :param request:
        :param context:
        :return:
        """
        response = {"waitAlterCase": [], "waitApplyCase": [], "extractCase": []}
        doctor = request.doctor
        with self.context.app.mysqlConnection.session() as session:
            waitAlterCaseCount = doctor_repository.query_wait_alter_case_list(session, doctor, response)
            patientType = self.context.app.config.get(Config.QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE, None)
            onlineStartTime = self.context.app.config.get(Config.QC_FIRST_ONLINE_PUBLISH_TIMESTAMP, None)
            waitApplyCaseCount = doctor_repository.query_wait_apply_case_list(session, doctor, response, patientType, onlineStartTime)
            extractCaseCount, extractNotReadCaseCount = doctor_repository.query_extract_case_list(session, doctor,
                                                                                                       response)
            threeDayStartTime, twoDayStartTime = doctor_repository.query_three_day_start_time(session)

            response["threeDayStartTime"]= threeDayStartTime
            response["twoDayStartTime"]= twoDayStartTime
            response["waitAlterCaseCount"]= waitAlterCaseCount
            response["waitApplyCaseCount"]= waitApplyCaseCount
            response["extractCaseCount"]= extractCaseCount
            response["extractNotReadCaseCount"]= extractNotReadCaseCount

        return response


class UpdateCaseIsRead(MyResource):

    @pre_request(request, ["caseIds:list"])
    def post(self):
        """
        更新抽检病历已读
        :param request:
        :param context:
        :return:
        """
        if not request.caseIds:
            return get_error_resp("无caseId信息")
        doctor_repository.update_extract_case_is_read(request)
        return g.result


class GetDoctorEMRProblemNum(MyResource):

    @pre_request(request, ["caseId", "doctor", "docIds"])
    def get(self):
        """
        获取emr文书外框架问题数
        :param request:
        :param context:
        :return:
        """
        response = {}
        caseId = request.caseId or ""
        if not caseId:
            # 前端需求，仅传doctorId时为查询医生待整改病历数
            total, firstNum, secondNum, thirdNum, doctorName = doctor_repository.query_doctor_refuse_num(request.doctor)
            response["problemCount"] = total
            response["doctorName"] = doctorName
            return response
        problemCount, doctorName = doctor_repository.query_emr_problem_count(request)

        response["problemCount"] = problemCount
        response["doctorName"] = doctorName
        return response
    
    
class GetDoctorEMRProblemList(MyResource):

    @pre_request(request, GetDoctorEMRProblemListReq)
    def get(self):
        """
        获取emr文书问题列表
        :param request:
        :param context:
        :return:
        """
        response = {"caseInfo": {}, "problemList": [], "problemSummary": {}, "auditInfo": {}}
        auditId = request.auditId or 0
        refuseTime = request.refuseTime or ""
        if auditId and refuseTime:
            doctor_repository.query_emr_assign_audit_record_problem_list(request, response)
        else:
            doctor_repository.query_emr_problem_list(request, response)
        return response


class GetDoctorEMRExtractProblemList(MyResource):

    @pre_request(request, GetDoctorEMRProblemListReq)
    def get(self):
        """
        获取emr文书抽检问题列表
        :param request:
        :param context:
        :return:
        """
        response = {"data": []}
        doctor_repository.query_emr_extract_problem_list(request, response)
        return response


class GetDoctorEMRAuditRecordList(MyResource):

    @pre_request(request, ["caseId", "doctor", "docIds"])
    def get(self):
        """
        获取emr文书质控流程列表
        :param request:
        :param context:
        :return:
        """
        response = {"data": []}
        doctor_repository.query_emr_audit_record(request, response)
        return response


class UpdateProblemFixFlag(MyResource):

    @pre_request(request, ["problemId:int"])
    def post(self):
        """
        问题整改完成
        :param request:
        :param context:
        :return:
        """
        doctor_repository.update_problem_fix(request)
        return g.result


class ProblemAppeal(MyResource):

    @pre_request(request, ["problemId:int", "appealInfo", "doctor"])
    def post(self):
        """
        问题申诉
        :param request:
        :param context:
        :return:
        """
        doctor_repository.update_problem_appeal(request)
        return g.result


class ProblemIgnore(MyResource):

    @pre_request(request, ["problemId:int"])
    def post(self):
        """
        问题忽略
        :param request:
        :param context:
        :return:
        """
        doctor_repository.update_problem_ignore(request)
        return g.result


class GetEMRCaseSubmitApplyList(MyResource):

    @pre_request(request, ["caseIds:list", "docIds:list"])
    def post(self):
        """
        emr提交病历申请列表
        :param request:
        :param context:
        :return:
        """
        response = {"data": []}
        if not request.caseIds:
            return get_error_resp("caseIds can not be empty.")
        doctor_veto = self.context.app.config.get(Config.QC_DOCTOR_VETO, 1) == 2
        doctor_repository.query_submit_apply_case_list(request, response, doctor_veto)
        return response


class EMRCaseSubmit(MyResource):

    @pre_request(request, ["caseIds:list", "doctor"])
    def post(self):
        """
        emr病历外提交
        :param request:
        :param context:
        :return:
        """
        doctor_repository.case_submit(request, g.result)
        return g.result


class EMRCaseTransfer(MyResource):

    @pre_request(request, ["caseIds:list", "doctor"])
    def post(self):
        """
        emr病历转科
        :param request:
        :param context:
        :return:
        """
        # todo emr给转科接口
        return g.result


class EMRDocSave(MyResource):

    @pre_request(request, ["caseId", "docId", "doctorId"])
    def post(self):
        """
        emr文书保存
        :param request:
        :param context:
        :return:
        """
        doctor_repository.emr_doc_save(request)
        return g.result


class EMRDocPartSave(MyResource):

    @pre_request(request, ["caseId", "docId", "doctorId"])
    def post(self):
        """
        emr文书部分保存
        :param request:
        :param context:
        :return:
        """
        doctor_repository.emr_doc_part_save(request, g.result)
        return g.result


class EMRDocDelete(MyResource):

    @pre_request(request, ["caseId", "docId", "doctorId"])
    def post(self):
        """
        emr文书删除
        :param request:
        :param context:
        :return:
        """
        doctor_repository.emr_doc_delete(request, g.result)
        return g.result


class GetCaseStatus(MyResource):

    @pre_request(request, ["caseId", "docIds", "doctor"])
    def get(self):
        """
        获取病历状态
        :param request:
        :param context:
        :return:
        """
        response = {}
        response["caseId"] = request.caseId
        response["status"] = doctor_repository.get_case_status(request.caseId)
        return response

    
class GetAppealNotReadCount(MyResource):

    @pre_request(request, ["doctorId"])
    def post(self):
        """
        当前医生查询未读申诉消息个数
        """
        response = {}
        appeal_repository.query_not_read_count(request, response)
        return response


class GetAppealNotReadCaseList(MyResource):

    @pre_request(request, ["doctorId"])
    def post(self):
        """
        当前医生查询未读申诉消息病历列表
        """
        response = {"data": []}
        appeal_repository.get_not_read_case_list(request, response)
        return response


class GetCaseAppealProblemList(MyResource):

    @pre_request(request, ["caseId", "doctorId", "auditType"])
    def post(self):
        """
        申诉病历问题列表
        """
        response = {"problemData": []}
        appeal_repository.get_problem_list(request, response)
        return response


class GetCaseAppealDetail(MyResource):

    @pre_request(request, ["caseId", "doctorId", "problemId"])
    def post(self):
        """
        病历问题申诉详情
        """
        response = {"appealData": []}
        appeal_repository.get_appeal_detail(request, response)
        return response


class AppealCreate(MyResource):

    @pre_request(request, AppealCreateReq)
    def post(self):
        """
        申诉创建
        """
        appeal_repository.create(request, g.result)
        return g.result


class AppealDelete(MyResource):

    @pre_request(request, ["appealId", "doctorId"])
    def post(self):
        """
        申诉删除
        """
        appeal_repository.delete(request, g.result)
        return g.result


class AppealProblemIsRead(MyResource):

    @pre_request(request, ["problemId", "doctorId"])
    def post(self):
        """
        更新申诉信息已读
        """
        appeal_repository.update_read(request, g.result)
        return g.result


class AppealModify(MyResource):

    @pre_request(request, ["appealId", "doctorId", "content"])
    def post(self):
        """
        申诉修改
        """
        appeal_repository.modify(request, g.result)
        return g.result


class MessageReceive(MyResource):

    @pre_request(request, MessageReceiveReq)
    def post(self):
        """接收需要发送的消息
        """
        find_func = {
            1: doctor_repository.send_create_msg,
        }
        if request.messageType not in find_func:
            return get_error_resp('消息类型不存在')
        find_func[request.messageType](request)
        return g.result


class EmrSaveDebug(MyResource):

    @pre_request(request, EmrSaveDebugReq)
    def post(self):
        """
        医生端debug, 记录日志
        """
        doctor_repository.logDebug(request, g.result)
        return g.result


class GetIpPlan(MyResource):

    def get(self):
        """
        IP黑名单接口
        """
        response = {}
        # grpc metadata 中没有 x-real-ip 只有 x-forwarded-for
        # flask 获取请求者ip非常简单, 直接request.remote_addr即可
        # logging.info(context.invocation_metadata())
        # client_ip = getFirstMetadataValue(context, "x-forwarded-for").split(',')[0].strip()
        client_ip = request.remote_addr
        logging.info(f"GetIpPlan: user ip: [{client_ip}]")

        # 根据配置项获取医生端插件开关，医生端开=>只有黑名单不显示，医生端关=>只有白名单显示
        doctor_switch = self.context.app.config.get(Config.QC_DOCTOR_SWITCH, None)
        if not doctor_switch or doctor_switch == "on":
            response["socketType"] = doctor_repository.get_ip_rule(client_ip)
        else:
            response["socketType"] = 1
            if doctor_repository.get_ip_rule(client_ip) == 2:
                response["socketType"] = 2
        return response


class ApplyArchive(MyResource):

    @pre_request(request, ["caseId", "doctor", "doctorName"])
    def get(self):
        """申请归档
        """
        doctor_repository.case_submit(ApplyArchiveRequest(caseIds=[request.caseId], doctor=request.doctor), g.result)
        return g.result


class TryCancelApplyArchive(MyResource):

    @pre_request(request, ["caseId"])
    def get(self):
        """查询是否可以撤销申请归档
        """
        response = {}
        caseInfo = self.context.getCaseApplication("hospital").getCaseDetail(caseId=request.caseId)
        if not caseInfo:
            return get_error_resp("病历号未找到")
        audit = self.context.getAuditApplication("hospital").getAuditRecordById(caseInfo.audit_id)
        response["caseId"] = request.caseId
        response["permitted"] = 0 if audit.isOperated() else 1
        return response










    




    
