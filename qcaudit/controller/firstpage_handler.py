#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   firstpage_handler.py
@Time    :   2023/06/27 11:15:26
@Author  :   zhangda 
@Desc    :   None
'''


from . import *
from qcaudit.env_config.pre_req import *
from qcaudit.common.const import *
from .qc_util import QCUtil
from qcaudit.service.protomarshaler import *
from qcaudit.config import Config
from qcaudit.utils.bidataprocess import BIFormConfig, BIDataProcess


class GetList(MyResource):

    @pre_request(request, GetFPListReq)
    def get(self):
        """
        编码质控-编码列表
        :param request:
        :param context:
        :return:
        """
        response = {"items": []}
        app = self.context.GetFirstpageApplication()
        req = app.getCaseListReq(request)
        items, count = app.getCaseList(req)
        for item in items:
            protoItem = {"caseTags": []}  # response.items.add()
            unmarshalCaseInfo(protoItem, item)
            response["items"].append(protoItem)
        response["total"] = count
        response["start"] = request.start or 0
        response["size"] = request.size or 15
        return response


class GetListExport(MyResource):

    @pre_request(request, GetFPListReq)
    def get(self):
        """
        编码质控-编码列表导出
        :param request:
        :param context:
        :return:
        """
        response = {}
        app = self.context.GetFirstpageApplication()
        req = app.getCaseListReq(request, is_export=1)
        data, count = app.getCaseList(req)

        file_name = "编码列表_{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
        file_id = app.get_file_id(file_name)
        path_file_name = export_path + file_id + ".xlsx"
        to_excel_data, data_yaml = app.format_case_list(data, request)

        cfg = BIFormConfig.fromYaml(data_yaml)
        processor = BIDataProcess(cfg, to_excel_data)
        processor.toExcel(path=path_file_name, sortBy=[("dischargeTime", -1)])

        response["id"] = file_id
        response["fileName"] = file_name

        return response
    
    
class GetCaseDiagnosis(MyResource):

    @pre_request(request, ["caseId", "syncFlag:int"])
    def post(self):
        """
        编码质控-病历诊断信息列表
        :param request:
        :param context:
        :return:
        """
        response = {"diagnosisInfo": [], "pathologyInfo": {}, "damageInfo": {}}
        app = self.context.GetFirstpageApplication()
        data = app.get_case_diagnosis(request)
        for diagnosis_info in data:
            if diagnosis_info.type == DIAGNOSIS_TYPE_0:
                protoItem = {}  # response.diagnosisInfo.add()
                unmarshal_diagnosis_info(protoItem, diagnosis_info)
                response["diagnosisInfo"].append(protoItem)
            elif diagnosis_info.type == DIAGNOSIS_TYPE_1:
                unmarshal_diagnosis_info(response["pathologyInfo"], diagnosis_info)
            elif diagnosis_info.type == DIAGNOSIS_TYPE_2:
                unmarshal_diagnosis_info(response["damageInfo"], diagnosis_info)

        return response


class GetDiagnosis(MyResource):

    @pre_request(request, ["isOrigin:int", "caseId", "input", "originName"])
    def get(self):
        """
        编码质控-诊断列表
        :param request:
        :param context:
        :return:
        """
        response = {"items": []}
        app = self.context.GetFirstpageApplication()
        base_dict = self.context.GetDiagnosisApplication().base_dict
        name_code_dict = self.context.GetDiagnosisApplication().name_code_dict
        data = app.get_diagnosis(request, base_dict=base_dict, name_code_dict=name_code_dict)
        for item in data:
            protoItem = {}  # response.items.add()
            if request.isOrigin == 1:
                unmarshalOriginCodeInfo(protoItem, item)
            else:
                unmarshalCodeInfo(protoItem, item)
            response["items"].append(protoItem)
        return response


class SaveCaseDiagnosis(MyResource):

    @pre_request(request, SaveCaseDiagnosisReq)
    def post(self):
        app = self.context.GetFirstpageApplication()
        g.result["isSuccess"] = app.save_case_diagnosis(request)
        return g.result


class DeleteCaseDiagnosis(MyResource):

    @pre_request(request, ["id:int"])
    def post(self):
        """
        编码质控-诊断信息删除
        :param request:
        :param context:
        :return:
        """
        if not request.id:
            return get_error_resp("id can not be empty.")
        app = self.context.GetFirstpageApplication()
        g.result["isSuccess"] = app.delete_case_diagnosis(request.id)
        return g.result


class GetCaseOperation(MyResource):

    @pre_request(request, ["caseId", "syncFlag:int"])
    def post(self):
        """
		编码质控-病历手术、操作信息列表
		:param request:
		:param context:
		:return:
		"""
        response = {"operationInfo": []}
        app = self.context.GetFirstpageApplication()
        if request.syncFlag:
            app.initOperationList(request.caseId)
        items = app.getOperationList(request.caseId)
        if not items:
            if not request.syncFlag and not app.query_is_first(request.caseId):
                app.initOperationList(request.caseId)
                items = app.getOperationList(request.caseId)
        for item in items:
            protoItem = {}  # response.operationInfo.add()
            unmarshalOperation(protoItem, item)
            response["operationInfo"].append(protoItem)
        return response


class GetOperation(MyResource):

    @pre_request(request, ["isOrigin:int", "caseId", "input", "originName"])
    def get(self):
        """
	    编码质控-手术、操作列表
		:param request:
		:param context:
		:return:
        """
        response = {"items": []}
        app = self.context.GetFirstpageApplication()
        base_dict = self.context.GetOperationApplication().base_dict
        name_code_dict = self.context.GetOperationApplication().name_code_dict
        name_type_dict = self.context.GetOperationApplication().name_type_dict
        items = app.getOperation(request, base_dict, name_code_dict, name_type_dict)
        for item in items:
            protoItem = {}  # response.items.add()
            if request.isOrigin == 1:
                unmarshalOriginOperCodeInfo(protoItem, item)
            else:
                unmarshalCodeInfo(protoItem, item)
            response["items"].append(protoItem)
        return response


class SaveCaseOperation(MyResource):

    @pre_request(request, SaveCaseDiagnosisReq)
    def post(self):
        """
		编码质控-手术、操作信息保存
		:param request:
		:param context:
		:return:
        """
        if not request.caseId or not request.operationInfo:
            return get_error_resp("caseId or operationInfo is empty.")
        app = self.context.GetFirstpageApplication()
        app.updateOperation(request.caseId, request.operationInfo, request.sortIds)
        g.result["id"] = request.operationInfo.id
        return g.result


class DeleteCaseOperation(MyResource):

    @pre_request(request, ["id:int"])
    def post(self):
        """
		编码质控-手术、操作信息删除
		:param request:
		:param context:
		:return:
        """
        if not request.id:
            return get_error_resp("id is empty.")
        app = self.context.GetFirstpageApplication()
        app.deleteOpertion(request.id)
        g.result["id"] = request.id
        return g.result


class GetNarcosis(MyResource):

    @pre_request(request, ["input"])
    def get(self):
        """
        编码质控-麻醉方式列表
        :param request:
        :param context:
        :return:
        """
        response = {"items": []}
        app = self.context.GetFirstpageApplication()
        data = app.get_narcosis(request.input)
        for item in data:
            protoItem = {}  # response.items.add()
            unmarshalCodeInfo(protoItem, item)
            response["items"].append(protoItem)
        return response


class SubmitCheck(MyResource):

    @pre_request(request, SaveCaseDiagnosisReq)
    def post(self):
        """
        编码质控-提交-检查
        :param request:
        :param context:
        :return:
        """
        response = {"problems": [], "total": 0}
        if not request.caseId or not request.operatorId or not request.operator:
            return get_error_resp("caseId or operator or operatorId is empty.")
        app = self.context.GetFirstpageApplication()
        result = app.submitCheck(request.caseId, request.operatorId, request.operator)
        if not result:
            response["total"] = 2
            response["problems"].append({"reason": "入院记录无病史陈述者"})
            response["problems"].append({"reason": "新增住院病人须知问题"})
            return response
        return response


class Submit(MyResource):

    @pre_request(request, SaveCaseDiagnosisReq)
    def post(self):
        """
        编码质控-提交-继续
        :param request:
        :param context:
        :return:
        """
        if not request.caseId or not request.operator or not request.operator:
            return get_error_resp("caseId or operator or operatorId is empty.")
        app = self.context.GetFirstpageApplication()
        status = app.submit(request.caseId, request.operatorId, request.operator)
        return g.result


class CaseDetail(MyResource):

    @pre_request(request, ["caseId"])
    def post(self):
        """
        编码质控-病历详情
        :param request:
        :param context:
        :return:
        """
        response = {}
        if not request.caseId:
            return get_error_resp("caseId can not be empty.")
        app = self.context.GetFirstpageApplication()
        item = app.getCaseDetail(request.caseId)
        if item:
            response["id"] = item.id or ''
            response["caseId"] = item.caseId or ''
            response["patientId"] = item.patientId or ''
            response["name"] = item.name or ''
            response["branch"] = item.branch or ''
            response["department"] = item.department or ''
            response["attendDoctor"] = item.attendDoctor or ''
            response["dischargeTime"] = item.dischargeTime.strftime('%Y-%m-%d %H:%M:%S') if item.dischargeTime else ''
            response["admitTime"] = item.admitTime.strftime('%Y-%m-%d %H:%M:%S') if item.admitTime else ''
            response["age"] = str(item.age) or ''
            response["gender"] = item.gender or ''
            response["inDepartment"] = item.outDeptName or ''
            response["inpDays"] = item.inpDays or 0
            if fp_info := item.fp_info:
                response["codeDoctor"] = fp_info.coder or ''
                response["codeTime"] = fp_info.code_time.strftime('%Y-%m-%d %H:%M:%S') if fp_info.code_time else ''
        return response








