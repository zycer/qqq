from . import *
from qcaudit.env_config.pre_req import *
from qcaudit.common.const import *
from .qc_util import QCUtil
from qcaudit.service.protomarshaler import *
from qcaudit.domain.sample.req import GetSampleRecordRequest, GetSampleDetailRequest
from qcaudit.config import Config
import uuid, random
from qcaudit.utils.bidataprocess import BIFormConfig, BIDataProcess
from qcaudit.utils.towebconfig import SAMPLE_HISTORY_EXPORT_DATA, SAMPLE_HISTORY_EXPORT_YAML, SAMPLE_HISTORY_GROUP_EXPORT_YAML


class GetSampleCase(MyResource):

    @pre_request(request, GetCaseListReq)
    def post(self):
        """获取抽取病历列表
        """
        response = {"items": []}
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        req = QCUtil.get_case_list_req(app, request)
        
        existCaseIds = list(request.existCaseIds) if request.existCaseIds else []
        caseList, total = app.getSampleCase(req, sampleBy=request.sampleBy, sampleNum=request.sampleCount, existedCaseIds=existCaseIds)

        for x in caseList:
            protoItem = {"caseTags": [], "timeline": {}}  # response.items.add()
            unmarshalCaseInfo(x, protoItem, request.auditType, is_sample=1)
            response["items"].append(protoItem)

        caseIds = [caseInfo.caseId for caseInfo in caseList]
        conditions = ["全部"]
        sampleBy = request.sampleBy
        # 抽取重点病历范围
        if sampleBy == SAMPLE_BY_TAG:
            all_tags = self.context.getCaseApplication(request.auditType).getCaseTag('') or []
            if len(all_tags) > len(request.tags):
                conditions = request.tags
            else:
                sampleBy = SAMPLE_BY_TAG_ALL
        # 抽取诊疗组范围
        if sampleBy == SAMPLE_BY_GROUP and request.group and request.group != "all":
            conditions = request.group.split(',')
        sample = app.record_sample_operation(request.sampleId, request.caseType, caseIds,
                                             operatorId=request.operatorId, operatorName=request.operatorName,
                                             sampleBy=sampleBy, sampleCount=request.sampleCount,
                                             existedCaseIds=existCaseIds, sampleFilter=conditions)
        response["sampleId"] = sample
        response["total"] = len(caseList)
        response["start"] = request.start
        response["size"] = len(caseList)
        return make_response(jsonify(response), 200)


class SubmitSampleCase(MyResource):

    @pre_request(request, SubmitSampleCaseReq)
    def post(self):
        """提交抽取结果
        """
        response = {}
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        sampleRecord = app.submitSampleResult(request.caseIds,request.auditType, request.caseType, request.operatorId, request.operatorName, request.sampleId)
        if not sampleRecord:
            return get_error_resp("提交失败")
        response["id"] = sampleRecord.id
        return make_response(jsonify(response), 200)


class GetSampleList(MyResource):

    @pre_request(request, GetSampleListReq)
    def get(self):
        """获取抽取记录列表
        """
        response = {"items": []}
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)

        req = GetSampleRecordRequest(**request.args)
        req.start = int(req.start or 0)
        req.size = int(req.size or 15)
        sampleList, totalCount = app.getSampleRecordHistory(req)
        count = 0
        for x in sampleList:
            protoItem = {"sampleBy": []}  # response.items.add()
            protoItem["id"] = x.id or 0
            protoItem["caseType"] = x.caseType or ""
            protoItem["auditType"] = x.auditType or ""
            protoItem["operatorId"] = x.operatorId or ""
            protoItem["operatorName"] = x.operatorName or ""
            protoItem["caseCount"] = x.sampledCount or 0
            protoItem["status"] = x.isAssigned or 0
            protoItem["extractTime"] = x.createdAt.strftime("%Y-%m-%d %H:%M:%S") if x.createdAt else ""
            if x.sampleBy:
                for by in x.sampleBy.split(','):
                    protoItem["sampleBy"].append(by)
            count += 1
            response["items"].append(protoItem)
        response["total"] = totalCount
        response["start"] = request.start
        response["size"] = count
        return make_response(jsonify(response), 200)


class GetSampleDetail(MyResource):

    @pre_request(request, GetSampleDetailReq)
    def post(self):
        """获取抽取记录详情列表
        """
        response = {"items": []}
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        if not request.sampleId:
            return get_error_resp("sampleId can not be empty." % request.sampleId)

        request_json = {k: v for k, v in request.json.items() if hasattr(GetSampleDetailRequest, k)}
        req = GetSampleDetailRequest(**request_json)
        sampleList, totalCount = app.getSampleDetail(req)
        count = 0
        caseTagDict = None
        try:
            caseTagDict = {t.code: t for t in self.context.getCaseApplication(request.auditType).getCaseTag('')}
        except Exception as e:
            print(e)

        for x in sampleList:
            protoItem = {"caseTags": []}  # response.items.add()
            unmarshalSampleDetail(protoItem, x, request, caseTagDict)
            response["items"].append(protoItem)
            count += 1
        response["total"] = totalCount
        response["start"] = request.start
        response["size"] = count
        return make_response(jsonify(response), 200)


class GetSampleDetailExport(MyResource):

    @pre_request(request, GetSampleDetailReq)
    def post(self):
        """
        抽取历史导出
        :return:
        """
        response = {}
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        request_json = {k: v for k, v in request.json.items() if hasattr(GetSampleDetailRequest, k)}
        req = GetSampleDetailRequest(**request_json)
        req.is_export = 1
        sampleList, totalCount = app.getSampleDetail(req)

        caseTagDict = {t.code: t for t in self.context.getCaseApplication(request.auditType).getCaseTag('')}

        patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME) or "病案号"
        base_file_name = EXPORT_FILE_AUDIT_TYPE.get(request.auditType) + "抽取历史" + "-{}.xlsx"
        file_name = base_file_name.format(datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(10, 99)))
        file_id = uuid.uuid4().hex
        path_file_name = export_path + file_id + ".xlsx"

        # df = app.writeSampleExcel(sampleList, request, caseTagDict, patient_id_name)
        # df.to_excel(path_file_name, index=False)
        data = app.format_sample_history_export_data(sampleList, request, caseTagDict, patient_id_name)

        group_yaml = SAMPLE_HISTORY_GROUP_EXPORT_YAML if int(app.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) else ""
        reason_column = 14 if int(app.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) else 13
        cfg = BIFormConfig.fromYaml(SAMPLE_HISTORY_EXPORT_YAML.format(patient_name=patient_id_name, group=group_yaml))
        processor = BIDataProcess(cfg, data)
        processor.toExcel(path=path_file_name, sortBy=[], column_width=[reason_column, 120])

        response["id"] = file_id
        response["fileName"] = file_name
        return make_response(jsonify(response), 200)


class AssignSample(MyResource):

    @pre_request(request, AssignSampleReq)
    def post(self):
        """分配抽取记录
        """
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.sampleId:
            return get_error_resp("auditType: %s or sampleId: %s is error." % (request.auditType, request.sampleId))
        app.assignExpert(request.sampleId, request.caseType, request.assignType, request.auditType, request.avoidSameDept)
        return make_response(jsonify(g.result), 200)


class AssignTask(MyResource):

    @pre_request(request, AssignTaskReq)
    def post(self):
        """指定分配任务
        """
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.expert["id"]:
            return get_error_resp("auditType: %s or expert.id: %s is error." % (request.auditType, request.expert["id"]))
        if (not request.many and not request.taskId) or (request.many and not request.taskIds):
            return get_error_resp("参数错误")
        recordId = app.assginExpertToItem(request.taskId, request.taskIds, request.expert["id"], request.expert["name"], request.many)
        app.checkSampleAssigned(recordId, request.auditType)
        return make_response(jsonify(g.result), 200)


class DeleteTask(MyResource):

    @pre_request(request, ["taskId", "auditType"])
    def post(self):
        """废除抽取任务
        """
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.taskId:
            return get_error_resp("auditType: %s or taskId: %s is error." % (request.auditType, request.taskId))
        app.removeTask(request.taskId)
        return make_response(jsonify(g.result), 200)


class GetExpertList(MyResource):

    @pre_request(request, ["auditType", "caseType"])
    def get(self):
        """获取特定类型的专家列表
        """
        response = {"experts": []}
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % (request.auditType))

        expertList = app.getExpertList(request.caseType)
        for x in expertList:
            protoItem = {}  # response.experts.add()
            protoItem["id"] = x.userId
            protoItem["name"] = x.userName if x.userName else ""
            response["experts"].append(protoItem)

        return response


class AddExpert(MyResource):

    @pre_request(request, AssignTaskReq)
    def post(self):
        """添加专家
        """
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.expert:
            return get_error_resp("auditType: %s is error." % (request.auditType))
        app.addExpert(request.expert["id"], request.expert["name"], request.caseType)
        return g.result


class DeleteExpert(MyResource):

    @pre_request(request, ["auditType", "caseType", "expertId"])
    def post(self):
        """删除专家
        """
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.expertId:
            return get_error_resp("auditType: %s or expertId: %s is error." % (request.auditType, request.expertId))
        app.removeExpert(request.expertId, request.caseType)
        return g.result


class BranchAssignTask(MyResource):

    @pre_request(request, BranchAssignTaskReq)
    def post(self):
        """
        按病区/科室 分配任务
        :return:
        """
        app = self.context.getSampleApplication(request.auditType)
        assign_flag = int(app.app.config.get(Config.QC_ASSIGN_DIMENSION) or 1)
        req = GetSampleDetailRequest(**request.json)
        req.is_export = 1
        sampleList, totalCount = app.getSampleDetail(req)
        to_be_assign_data = {}
        # 先查询待分配数据
        for item in sampleList:
            ar_status = getattr(item.auditRecord, AuditRecord.getOperatorFields(auditType=request.auditType).statusField)
            if ar_status != 1 or item.model.isMannalAssigned == 1:
                continue
            case_field = (item.caseModel.outDeptName or item.caseModel.department) if assign_flag == 1 else item.caseModel.wardName
            if case_field not in to_be_assign_data:
                to_be_assign_data[case_field] = []
            to_be_assign_data[case_field].append(item.model.id)
        if request.wardDoctor:
            # 如果病区分配医生有变动则更新
            app.update_wardDoctor(request.doctorId, request.wardDoctor, assign_flag)
        if not to_be_assign_data:
            # 无数据可分配
            return g.result
        # 再查询病区分配数据
        ward_doctor_dict = app.get_ward_doctor_dict(request.doctorId, assign_flag)
        for ward, sample_item_ids in to_be_assign_data.items():
            expert_id = ward_doctor_dict.get(ward, {}).get("doctorId", "")
            expert_name = ward_doctor_dict.get(ward, {}).get("doctorName", "")
            isMannalAssigned = 2
            if not expert_id or not expert_name:
                # 支持将已经病区分配过的病历, 病区分配医生清空, 恢复到未分配前(支持平均分配)
                # print("BranchAssignTask, ward: %s, sample_item_ids: %s, assign no expert" % (ward, sample_item_ids))
                isMannalAssigned = 0
            app.ward_assign(sample_item_ids, expert_id, expert_name, isMannalAssigned)
        return g.result


class BranchAssignDoctorList(MyResource):

    @pre_request(request, ["doctorId"])
    def post(self):
        """
        按病区分配医生列表
        :return:
        """
        response = {"items": []}
        app = self.context.getSampleApplication("hospital")
        if not request.doctorId:
            return get_error_resp("doctorId can not be empty.")
        assign_flag = int(app.app.config.get(Config.QC_ASSIGN_DIMENSION))
        data = app.query_wardDoctor_from_ward_doctor(request.doctorId, assign_flag)
        if data:
            tmp_ICU_list = []
            for item in data:
                if "ICU" in item.ward:
                    tmp_ICU_list.append(item)
                    continue
                protoItem = {}  # response.items.add()
                protoItem["ward"] = item.ward
                protoItem["doctorName"] = item.doctorName or ""
                protoItem["doctorId"] = item.doctorId or ""
                response["items"].append(protoItem)
            for item in tmp_ICU_list:
                protoItem = {}  # response.items.add()
                protoItem["ward"] = item.ward
                protoItem["doctorName"] = item.doctorName or ""
                protoItem["doctorId"] = item.doctorId or ""
                response["items"].append(protoItem)
        else:
            data = app.query_wardDoctor_from_ward(assign_flag)
            tmp_ICU_list = []
            for item in data:
                if "ICU" in item.name:
                    tmp_ICU_list.append(item.name)
                    continue
                protoItem = {}  # response.items.add()
                protoItem["ward"] = item.name
                response["items"].append(protoItem)
            for name in tmp_ICU_list:
                protoItem = {}  # response.items.add()
                protoItem["ward"] = name
                response["items"].append(protoItem)
        return response


class UpdateSampleCase(MyResource):

    @pre_request(request, UpdateSampleCaseReq)
    def post(self):
        """更新病历库结果
        """
        response = {}
        app = self.context.getSampleApplication(request.auditType)
        sampleId = app.update_sample_case(request.sampleId, request.caseType, request.caseIds, request.operatorId, request.operatorName)
        if sampleId:
            response["id"] = sampleId
            response["isSuccess"] = "True"
        return response
    
    
class GetSampleOperation(MyResource):

    @pre_request(request, ["id:int", "start:int", "size:int"])
    def get(self):
        """获取病历抽取规则留痕
        """
        response = {"operations": []}
        app = self.context.getSampleApplication("hospital")
        sample, operations = app.getSampleOperations(request.id)
        if sample:
            response["sampleId"] = sample.id
            response["sampleCount"] = sample.sampledCount
        for operation in operations[request.start: request.start+request.size]:
            protoItem = {"filter": {"conditions": []}}  # response.operations.add()
            protoItem["name"] = operation.name
            protoItem["content"] = operation.content
            protoItem["filter"]["sampleBy"] = operation.sample_by
            if operation.conditions:
                data = {'全部': "全部"}
                if operation.sample_by == SAMPLE_BY_TAG:
                    data = {t.code: t.icon for t in self.context.getCaseApplication('hospital').getCaseTag('')}
                for item in operation.conditions.split(','):
                    protoItem["filter"]["conditions"].append(data.get(item, item))
            protoItem["sampleCount"] = operation.sampled_count
            protoItem["operator"] = operation.operator
            response["operations"].append(protoItem)
        response["total"] = len(operations)
        response["size"] = request.size
        response["start"] = request.start
        return response


class SampleFilterList(MyResource):

    @pre_request(request, SampleFilterListReq)
    def get(self):
        """
        抽取管理-抽取条件列表
        :return:
        """
        response = {"data": []}
        app = self.context.getSampleApplication("hospital")
        filter_data, response.total = app.getSampleFilterList(request)
        all_tags = self.context.getCaseApplication(request.auditType).getCaseTag('') or []
        tag_dict = {tag.code: str(tag.icon) for tag in all_tags}
        for item in filter_data:
            protoItem = {"filter": {}}  # response.data.add()
            protoItem["id"] = item.id
            protoItem["name"] = item.name or ""
            protoItem["createTime"] = item.create_time.strftime("%Y-%m-%d") if item.create_time else ""
            protoItem["describe"] = item.describe or ""
            sample_filter = json.loads(item.filter)
            sample_range = item.range or ""
            if sample_filter.get("sampleBy") == "tag":
                if sample_range != "全部":
                    tag_icons = []
                    for tag in json.loads(sample_range):
                        tag_icons.append(str(tag_dict.get(tag)))
                    sample_range = json.dumps(tag_icons)
            protoItem["range"] = sample_range
            protoItem["range"] = sample_filter
            response["data"].append(protoItem)
        return response


class SampleFilterSave(MyResource):

    @pre_request(request, SampleFilterSaveReq)
    def post(self):
        """
        抽取管理-抽取条件保存
        :return:
        """
        app = self.context.getSampleApplication("hospital")
        all_tags = []
        if request.filter["sampleBy"] == SAMPLE_BY_TAG:
            all_tags = self.context.getCaseApplication(request.auditType).getCaseTag('') or []
        g.result["isSuccess"], g.result["message"] = app.saveSampleFilter(request, all_tags=all_tags)
        return g.result


class SampleTaskList(MyResource):

    @pre_request(request, SampleTaskListReq)
    def get(self):
        """
        抽取管理-抽取定时任务列表
        :return:
        """
        response = {"data": []}
        app = self.context.getSampleApplication("hospital")
        data, response["total"] = app.getSampleTaskList(request)
        for item in data:
            protoItem = {"assignDoctor": []}  # response.data.add()
            protoItem["id"]= item.id
            protoItem["name"]= item.name or ""
            protoItem["createTime"]= item.create_time.strftime("%Y-%m-%d") if item.create_time else ""
            protoItem["firstSampleTime"]= item.first_sample_time.strftime("%Y-%m-%d") if item.first_sample_time else ""
            protoItem["type"]= item.type or ""
            protoItem["days"]= str(item.days or "")
            protoItem["status"]= item.status or 0
            protoItem["notCurrentDeptFlag"]= item.notCurrentDeptFlag or 0
            protoItem["sampleFilter"]= json.loads(item.sample_filter)
            protoItem["queryFilter"]= json.loads(item.query_filter)
            assign_doctor = json.loads(item.assign_doctor or json.dumps([]))
            if assign_doctor:
                protoItem["assignDoctor"] = assign_doctor
            response["data"].append(protoItem)
        return response


class SampleTaskSave(MyResource):

    @pre_request(request, SampleTaskSaveReq)
    def post(self):
        """
        抽取管理-抽取定时任务保存
        :return:
        """
        response = {}
        app = self.context.getSampleApplication("hospital")
        response["id"], response["isSuccess"], response["message"] = app.saveSampleTask(request)
        return response



