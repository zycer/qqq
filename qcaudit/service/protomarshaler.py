#!/usr/bin/env python3
"""
模型转换
"""
import json
import logging

from qcaudit.common.const import AUDIT_STATUS, RECHECK_STATUS, CASE_STATUS_ARCHIVED, CASE_STATUS_REFUSED, \
	CASE_STATUS_APPLIED, CASE_STATUS_NOTAPPLIED, LAB_ABNORMAL_ICON, AUDIT_TYPE_ACTIVE, QCITEM_CATEGORY
from qcaudit.domain.audit.auditrecord import AuditRecord, AuditHistoryItem
from qcaudit.domain.problem.problem import ProblemSumTags
from qcaudit.domain.qcgroup.qcitem import QcItem
from qcaudit.domain.sample.samplerecorditem import SampleRecordItem
from datetime import datetime
from qcaudit.common.const import EXPORT_FILE_AUDIT_TYPE
from typing import Dict

def parseGender(gender):
	if not gender:
		return ""
	if gender == "F" or gender == "f":
		gender = "女"
	elif gender == "M" or gender == "m":
		gender = "男"
	return gender


# 状态编号转名称
def parseStatus(isFinal, status, auto_review=False, refused=False):
	if not isFinal:
		for item in AUDIT_STATUS:
			if item.get('dbid') == status:
				return item.get('returnid', status)
	else:
		for item in RECHECK_STATUS:
			if item.get('dbid') == status:
				return item.get('returnid', status)
	return 0


# 状态编号转名称
def parseStatusName(isFinal, status, auto_review=False, refused=False):
	if not isFinal:
		for item in AUDIT_STATUS:
			if item.get('dbid') == status:
				return item.get('name')
	else:
		for item in RECHECK_STATUS:
			if item.get('dbid') == status:
				return item.get('name')
	return ""


def parseRating(score):
	result = ""
	if score is None:
		return result
	if float(score) >= 90:
		result = "甲"
	elif float(score) >= 80:
		result = "乙"
	elif float(score) > 0:
		result = "丙"
	return result


def parseCaseStatus(status):
	if status == CASE_STATUS_APPLIED:
		return "待审核"
	elif status == CASE_STATUS_ARCHIVED:
		return "已归档"
	elif status == CASE_STATUS_REFUSED:
		return "已退回"
	elif status == CASE_STATUS_NOTAPPLIED:
		return "未申请"
	return ""


def getProblemButtonStatus(isFinal, status):
	if isFinal:
		if status == 3:
			return 1
		return 2
	else:
		if status == 1:
			return 1
	return 2


def unmarshalCaseInfo(caseInfo, protoItem, auditType, isFinal=False, is_sample=0, nowStatusFlag=0, diagnosis_data={}, operation_data={}):
	"""病历基本信息转换
	"""
	if not caseInfo:
		return
	protoItem["id"]= caseInfo.id or 0
	protoItem["caseId"]= caseInfo.caseId or ""
	protoItem["patientId"]= caseInfo.inpNo or caseInfo.patientId or ""
	protoItem["name"]= caseInfo.name or ""
	protoItem["gender"]= parseGender(caseInfo.gender)
	protoItem["age"]= f'{caseInfo.age or ""}{caseInfo.ageUnit or ""}'
	protoItem["hospital"]= caseInfo.hospital or ""
	protoItem["branch"]= caseInfo.branch or ""
	protoItem["attendDoctor"]= caseInfo.attendDoctor or ""
	protoItem["admitTime"]= caseInfo.admitTime.strftime('%Y-%m-%d') if caseInfo.admitTime else ""
	protoItem["dischargeTime"]= caseInfo.dischargeTime.strftime('%Y-%m-%d') if caseInfo.dischargeTime else ""
	if caseInfo.dischargeTime:
		protoItem["inpDays"]= caseInfo.inpDays or 0
	if caseInfo.dischargeTime:
		if caseInfo.status == CASE_STATUS_ARCHIVED:
			protoItem["caseType"]= "archive"
		else:
			protoItem["caseType"]= 'final'
	else:
		protoItem["caseType"]= 'active'
		protoItem["inpDays"]= (datetime.now() - caseInfo.admitTime).days if caseInfo.admitTime else 0
		if protoItem["inpDays"]< 0:
			protoItem["inpDays"]= 0

	protoItem["applyTime"]= caseInfo.applyTime.strftime('%Y-%m-%d') if caseInfo.applyTime else ""
	protoItem["applyDoctor"]= caseInfo.applyDoctor or ""
	if caseInfo.auditRecord is not None:
		auditRecord = AuditRecord(caseInfo.auditRecord)
		if auditRecord.getStatus(auditType, isFinal) == AuditRecord.STATUS_RECHECK_REFUSED:
			protoItem["checkRefused"]= 1
			protoItem["checkRefuseTime"]= auditRecord.getReviewTime(auditType, isFinal=True).strftime('%Y-%m-%d') if auditRecord.getReviewTime(auditType, isFinal=True) else ""
			protoItem["checkRefuseDoctor"]= auditRecord.getReviewer(auditType, isFinal=True)[1] or ""
			protoItem["checkRefuseReason"]= auditRecord.getFinalRefuseMessage(auditType) or ""
		protoItem["auditDoctor"]= auditRecord.getReviewer(auditType, isFinal=False)[1] or ""
		protoItem["auditTime"]= auditRecord.getReviewTime(auditType, isFinal=False).strftime('%Y-%m-%d') if auditRecord.getReviewTime(auditType, isFinal=False) else ""
		protoItem["reviewer"]= auditRecord.getReviewer(auditType, isFinal=True)[1] or ""
		protoItem["reviewTime"]= auditRecord.getReviewTime(auditType, isFinal=True).strftime('%Y-%m-%d') if auditRecord.getReviewTime(auditType, isFinal=True) else ""
		protoItem["status"]= parseStatus(isFinal, auditRecord.getStatus(auditType, isFinal))
		protoItem["statusName"]= parseStatusName(isFinal, auditRecord.getStatus(auditType), refused=caseInfo.refuseCount > 0)
		protoItem["problemCount"]= auditRecord.getProblemCount(auditType)
		if auditRecord.getScore(auditType) is not None:
			protoItem["caseScore"]= '{:g}'.format(auditRecord.getScore(auditType))
		if auditRecord.getFirstPageScore(auditType) is not None:
			protoItem["firstpageScore"]= '{:g}'.format(auditRecord.getFirstPageScore(auditType))
		protoItem["caseRating"]= parseRating(auditRecord.getScore(auditType))
		if protoItem["caseType"]== 'archive' and not is_sample:
			protoItem["archiveScore"]= '{:g}'.format(auditRecord.getArchiveScore())
			protoItem["archiveRating"]= parseRating(auditRecord.getArchiveScore())
			protoItem["archiveFPScore"]= '{:g}'.format(auditRecord.getArchiveFPScore())
		# 显示最新的审核流程节点
		if auditRecord.getTimeline():
			timeline = auditRecord.getTimeline()[-1]
			protoItem["timeline"]["time"]= str(datetime.strptime(timeline.time, '%Y-%m-%d %H:%M:%S').date()) if timeline.time else ''
			protoItem["timeline"]["action"]= timeline.action or ''
			protoItem["timeline"]["auditType"]= EXPORT_FILE_AUDIT_TYPE.get(timeline.auditType, '')+'质控' if timeline.auditType else ''
		protoItem["receiveTime"]= auditRecord.receiveTime.strftime('%Y-%m-%d') if auditRecord.receiveTime else ''
		# 科室质控被催办标记
		if auditType == 'department':
			protoItem["urgeFlag"]= auditRecord.getUrgeFlag()
	protoItem["assignDoctor"] = ""
	if caseInfo.sampleRecordItem is not None:
		sampleRecord = SampleRecordItem(caseInfo.sampleRecordItem)
		protoItem["assignDoctor"]= sampleRecord.getAssignExpert()[1] or ""
	
	protoItem["isDead"]= "死亡" if caseInfo.isDead else "未死亡"
	protoItem["visitTimes"]= caseInfo.visitTimes or 0
	protoItem["autoReviewFlag"]= caseInfo.autoReviewFlag or 0
	diag = caseInfo.diagnosis or diagnosis_data.get(caseInfo.caseId) or ""
	diag1 = diagnosis_data.get(caseInfo.caseId) or caseInfo.diagnosis or ""
	# 事中质控优先拿诊断表所有诊断, 而非主诊断
	protoItem["diagnosis"]= diag1 if auditType == AUDIT_TYPE_ACTIVE else diag
	protoItem["ward"]= caseInfo.wardName or ""
	protoItem["bedno"]= caseInfo.bedId or ""
	protoItem["dischargeDept"]= caseInfo.outDeptName or ""
	protoItem["inDepartment"]= caseInfo.department or ""
	protoItem["department"]= protoItem["dischargeDept"]or caseInfo.department or ""
	protoItem["refuseCount"]= caseInfo.refuseCount or 0
	protoItem["auditType"]= auditType
	protoItem["lastUpdateTime"]= caseInfo.updateTime.strftime('%Y-%m-%d %H:%M:%S') if caseInfo.updateTime else ""
	protoItem["caseTags"] = []
	caseTags = []
	if caseInfo.TagsModel:
		for tag in caseInfo.TagsModel:
			caseTags.append({"name": tag.name or "", "code": tag.code, "icon": tag.icon.decode() or ""})
		protoItem["caseTags"] = caseTags
	protoItem["residentDoctor"] = ""
	protoItem["chiefDoctor"] = ""
	protoItem["fellowDoctor"] = ""
	if caseInfo.firstPage:
		protoItem["residentDoctor"]= caseInfo.firstPage.resident_doctor or ""
		protoItem["chiefDoctor"]= caseInfo.firstPage.chief_doctor or ""
		protoItem["fellowDoctor"]= caseInfo.firstPage.attend_doctor or ""
	protoItem["group"]= caseInfo.medicalGroupName or ""
	protoItem["cost"]= '{:g}'.format(caseInfo.current_total_cost or 0)
	protoItem["activeQcNum"]= caseInfo.activeQcNum or 0
	protoItem["activeManProblemNum"]= caseInfo.activeProblemNum or 0
	protoItem["activeProblemStatus"]= getActiveProblemStatus(caseInfo.activeProblemNoFixNum, caseInfo.activeProblemNum)
	protoItem["operation"]= operation_data.get(caseInfo.caseId, {}).get("name") or ""
	oper_time = operation_data.get(caseInfo.caseId, {}).get("time")
	protoItem["operationDays"] = 0
	if oper_time:
		protoItem["operationDays"]= (datetime.now() - oper_time).days
	if auditType == AUDIT_TYPE_ACTIVE:
		score = float(caseInfo.activeAllScore or 100)
		if score < 0:
			score = 0
		protoItem["caseScore"]= '{:g}'.format(score)
		protoItem["caseRating"]= parseRating(score)
		protoItem["problemCount"]= int(caseInfo.activeAllProblemNum or 0)
		if caseInfo.active_record:
			protoItem["auditDoctor"]= caseInfo.active_record.operator_name or ""
			protoItem["auditTime"]= caseInfo.active_record.create_time.strftime('%Y-%m-%d') if caseInfo.active_record.create_time else ""


def unmarshalCaseEmr(emr, htmlDict, protoItem, contentsDict=None):
	if not emr:
		return
	protoItem["id"]= emr.id or 0
	protoItem["docId"]= emr.docId or ""
	protoItem["caseId"]= emr.caseId or ""
	protoItem["documentName"]= emr.documentName or ""
	protoItem["department"]= emr.department or ""
	protoItem["author"]= emr.author or ""
	# 历史遗留问题，前端显示的书写时间用的是createTime字段
	protoItem["createTime"]= emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
	protoItem["updateTime"]= emr.updateTime.strftime('%Y-%m-%d %H:%M:%S') if emr.updateTime else ""
	protoItem["recordTime"]= emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
	if hasattr(emr, "signTime"):
		protoItem["signTime"]= emr.signTime.strftime('%Y-%m-%d %H:%M:%S') if emr.signTime else ""
	protoItem["isSave"]= emr.isSave or False
	protoItem["isCheck"]= emr.checkFlag or False
	protoItem["htmlContent"]= htmlDict.get(emr.emrContentId, "")
	protoItem["contents"]= str(contentsDict.get(emr.emrContentId, {})) if contentsDict else ""
	protoItem["refuseDoctor"]= emr.refuseCode or ""
	protoItem["firstSaveTime"]= emr.first_save_time.strftime('%Y-%m-%d %H:%M:%S') if emr.first_save_time else ""
	# if hasattr(protoItem, "docTypes"):
	protoItem["docTypes"] = []
	for doc_type in emr.getDocTypes():
		protoItem["docTypes"].append(doc_type)

def unmarshalProblem(problem, protoItem, auditType="hospital", have_appeal_dict=None):
	item_type_dict = {1: '通用', 2: "专科", 3: "专病"}
	if not have_appeal_dict:
		have_appeal_dict = {}
	if not problem:
		return
	protoItem["id"]= problem.id or 0
	protoItem["caseId"]= problem.caseId or ""
	protoItem["docId"]= problem.docId or ""
	protoItem["docName"]= problem.title or ""
	if problem.emrInfoModel:
		recordTime = problem.emrInfoModel.recordTime.strftime('%Y-%m-%d') if problem.emrInfoModel.recordTime else ""
		protoItem["docName"]= f'{problem.emrInfoModel.documentName} {recordTime}'
	protoItem["qcItemId"]= problem.qcItemId or 0
	protoItem["instruction"]= problem.reason or ""
	protoItem["comment"]= problem.comment or ""
	protoItem["creator"]= problem.operator_name or ""
	protoItem["createTime"]= problem.created_at.strftime('%Y-%m-%d %H:%M') if problem.created_at else ""
	protoItem["deductFlag"]= problem.deduct_flag or 0
	protoItem["score"]= '{:g}'.format(float(problem.score))
	protoItem["deductSum"]= '{:g}'.format(float(problem.getScore()))
	protoItem["isFromAi"]= problem.fromAi()
	protoItem["counting"]= problem.problem_count or 0
	protoItem["refer"]= problem.refer or ""
	protoItem["appeal"]= problem.appeal or ""
	protoItem["appealDoctor"]= problem.appeal_doctor or ""
	protoItem["refuseFlag"]= 2 if problem.refuseCount and problem.refuseCount > 0 else 1
	protoItem["refuseDoctor"]= problem.doctorCode or ""
	protoItem["doctorName"]= problem.doctor or ""
	have_appeal_list = have_appeal_dict.get(int(problem.id), [0, 0])
	protoItem["haveAppeal"]= have_appeal_list[0]
	protoItem["haveNotReadAppeal"]= have_appeal_list[1]
	protoItem["tags"].extend(problem.getTags())
	protoItem["tipProblem"]= 1
	if problem.qcItemModel:
		qcitem = QcItem(problem.qcItemModel)
		protoItem["isFirstRequired"]= qcitem.isFPRequired()
		protoItem["tags"].extend(qcitem.getTags())
		protoItem["typeName"]= item_type_dict.get(problem.qcItemModel.type, "")
		# 问题类型
		if qcitem.enableType != 1 and not problem.status:
			protoItem["tipProblem"]= qcitem.enableType or 0


def unmarshalCheckHistory(history, protoItem):
	if not history:
		return
	protoItem["id"]= history.id
	protoItem["action"]= history.action
	protoItem["content"]= history.content
	protoItem["type"]= history.type
	protoItem["comment"]= history.comment
	protoItem["operatorId"]= history.operatorId
	protoItem["operatorName"]= history.operatorName
	protoItem["operateTime"]= history.created_at.strftime("%Y-%m-%d %H:%M") if history.created_at else ""


def unmarshalMedicalAdvice(order, protoItem, only_data=False):
	if not order:
		return
	protoItem["orderNo"]= order.order_no or ""
	protoItem["orderType"]= order.order_type or ""
	protoItem["setNo"]= order.set_no or ""
	protoItem["orderSeq"]= order.order_seq or ""
	protoItem["dateStart"]= order.date_start.strftime('%Y-%m-%d %H:%M') if order.date_start else ""
	protoItem["dateEnd"]= order.date_stop.strftime('%Y-%m-%d %H:%M') if order.date_stop else ""
	protoItem["orderCode"]= order.code or ""
	protoItem["orderName"]= order.name or ""
	protoItem["orderModel"]= order.model.model or ""
	protoItem["dosage"]= order.dosage or ""
	protoItem["dosageUnit"]= order.unit or ""
	protoItem["admission"]= order.instruct_code or ""
	protoItem["admissionName"]= order.instruct_name or ""
	protoItem["frequency"]= order.frequency_code or ""
	protoItem["frequencyName"]= order.frequency_name or ""
	protoItem["atTime"]= order.at_time or ""
	protoItem["creatorCode"]= order.doctor_code or ""
	protoItem["creatorName"]= order.doctor or ""
	if only_data:
		protoItem["createTime"]= order.create_at.strftime('%Y-%m-%d %H:%M:%S') if order.create_at else ""
	else:
		protoItem["createTime"]= order.create_at.strftime('%Y-%m-%d') if order.create_at else ""
	protoItem["stopDoctor"]= order.stop_doctor_code or ""
	protoItem["stopDoctorName"]= order.stop_doctor or ""
	protoItem["execTime"]= order.do_date or ""
	protoItem["nurse"]= order.nurse or ""
	protoItem["execDeptId"]= order.dept_code or ""
	protoItem["execDeptName"]= order.dept_name or ""
	protoItem["doFlag"]= order.status or ""
	protoItem["orderFlag"]= order.order_flag or ""
	protoItem["orderFlagName"]= order.order_flag_name or ""
	protoItem["selfFlag"]= order.self_flag or ""
	protoItem["printFlag"]= order.print_flag or ""
	protoItem["remark"]= order.remark or ""
	protoItem["totalDosage"]= order.total_dosage or ""
	protoItem["npl"]= order.npl or ""
	protoItem["dosageDay"]= order.dosage_day or ""
	protoItem["orderStatus"]= str(order.exec_flag) if order.exec_flag else ""


def unmarshalAuditTimeline(timeline, protoItem):
	if not timeline:
		return
	protoItem["time"]= timeline.time
	protoItem["doctor"]= timeline.doctor
	protoItem["action"]= timeline.action
	protoItem["auditId"]= timeline.auditId
	protoItem["auditType"]= timeline.auditType
	protoItem["actionType"]= AuditHistoryItem.ActionType.get(timeline.action, '')
	if timeline.action in [AuditHistoryItem.ACTION_REFUSE, AuditHistoryItem.ACTION_ADD_REFUSE]:
		protoItem["problemFlag"]= 1


def setRequestStatus(reqObj, auditType, auditStep, status):
	if auditStep == 'audit':
		# 质控
		if status:
			for s in AUDIT_STATUS:
				if s.get('hideflag'):
					continue
				if s.get('returnid') == status:
					reqObj['status'] = s.get('filter')
					break
			return
		# 全部状态
		reqObj['status'] = []
		for s in AUDIT_STATUS:
			if s.get('hideflag'):
				continue
			if s.get('filter'):
				reqObj['status'].extend(s.get('filter'))
	elif auditStep == 'recheck':
		# 审核
		if status:
			for s in RECHECK_STATUS:
				if s.get('hideflag'):
					continue
				if s.get('returnid') == status:
					reqObj['status'] = s.get('filter')
					break
			return
		reqObj['status'] = []
		for s in RECHECK_STATUS:
			if s.get('hideflag'):
				continue
			if s.get('filter'):
				reqObj['status'].extend(s.get('filter'))


def unmarshalQcItem(qcitem, protoItem):
	if not qcitem:
		return
	protoItem["id"]= qcitem.id
	protoItem["code"]= qcitem.code or ''
	protoItem["requirement"]= qcitem.requirement or ''
	protoItem["instruction"]= qcitem.instruction or ''
	protoItem["emrName"]= qcitem.standard_emr or ''
	linkEmr = qcitem.linkEmr or ""
	for item in linkEmr.split(","):
		if item:
			protoItem.linkEmr.append(item)
	protoItem["rule"]= qcitem.rule or ''
	protoItem["createTime"]= qcitem.created_at.strftime('%Y-%m-%d') if qcitem.created_at else ''
	protoItem["status"]= qcitem.approve_status or 0
	protoItem["custom"]= 1 if qcitem.custom == 1 else 2
	protoItem["enable"]= qcitem.enable or 0
	protoItem["enableType"]= qcitem.enableType or 1
	protoItem["veto"]= qcitem.veto or 0
	protoItem["category"]= qcitem.category or 0
	protoItem["type"]= qcitem.type or 0
	if qcitem.departments:
		protoItem["departments"].extend(qcitem.departments.split(','))
	if qcitem.disease:
		protoItem["disease"].extend(qcitem.disease.split(','))
	if qcitem.ruleModel:
		protoItem["remindInfo.field"]= qcitem.ruleModel.field or ""
		protoItem["remindInfo.firstHour"]= '{:g}'.format(float(qcitem.ruleModel.firstHour)) if qcitem.ruleModel.firstHour else ""
		protoItem["remindInfo.overHour"]= '{:g}'.format(float(qcitem.ruleModel.overHour)) if qcitem.ruleModel.overHour else ""
		protoItem["includeQuery"]= qcitem.ruleModel.includeQuery or ""
		protoItem["excludeQuery"]= qcitem.ruleModel.excludeQuery or ""

def unmarshalDiffProblem(protoItem, problems, problemsCount, title):
	protoItem["title"]= title
	protoItem["count"]= problemsCount
	for p in problems:
		if p.fromAi == 1:
			protoItem["confirmed"]+= 1
		else:
			protoItem["addByDr"]+= 1
		problemItem = {}# protoItem.data.add()
		problemItem["id"]= p.id
		problemItem["qcItemId"]= p.getQcItemId()
		problemItem["caseId"]= p.caseId or ""
		problemItem["docId"]= p.getDocId()
		problemItem["instruction"]= p.getReason()
		problemItem["comment"]= p.comment or ""
		problemItem["isFromAi"]= p.fromAi()
		problemItem["creator"]= p.getOperatorName()
		problemItem["refer"]= p.refer or ""
		problemItem["createTime"]= p.getCreateTime()
		problemItem["deductFlag"]= p.getDeductFlag()
		problemItem["score"]= str(p.getScore())
		problemItem["counting"]= p.getProblemCount()
		protoItem["data"].append(problemItem)


def unmarshalAssay(assay, protoItem):
	if not assay or not assay.content.result:
		return
	protoItem["reportId"] = str(assay.content.id) or ''
	protoItem["assayCode"] = assay.assayCode or ''
	protoItem["assayName"] = assay.testname or ''
	protoItem["result"] = assay.assayResult or ''
	protoItem["reference"] = assay.assayReference or ''
	protoItem["unit"] = assay.assayUnit or ''
	protoItem["abnormal"] = str(assay.assayAbnormal) if assay.assayAbnormal else ''
	protoItem["reportTime"] = assay.reportTime.strftime('%Y-%m-%d %H:%M:%S') if assay.reportTime else ''
	protoItem["assayItemName"] = ''
	if assay.content:
		protoItem["assayItemName"] = assay.content.itemname or ''


def unmarshalExamination(exam, protoItem):
	if not exam or not exam.examResult:
		return
	protoItem["examId"]= str(exam.content.id) or ''
	protoItem["examName"]= exam.examname or ''
	protoItem["examType"]= exam.examtype or ''
	protoItem["position"]= exam.position or ''
	protoItem["desc"]= exam.examDesc or ''
	protoItem["result"]= exam.examResult or ''
	protoItem["reportTime"]= exam.reportTime.strftime('%Y-%m-%d %H:%M:%S') if exam.reportTime else ''
	protoItem["requestTime"]= exam.requestTime.strftime('%Y-%m-%d %H:%M:%S') if exam.requestTime else ''
	protoItem["requestDoctor"]= exam.requestDoctor or ''
	protoItem["reqDept"]= exam.requestDepartment or ''


def unmarshalFirstPageInfo(protoItem, firstPageInfo):
	if not firstPageInfo:
		return
	protoItem["id"] = firstPageInfo.id or ''
	protoItem["caseId"] = firstPageInfo.caseId or ''
	protoItem["patientId"] = firstPageInfo.patientId or ''
	protoItem["sex"] = firstPageInfo.psex or ''
	protoItem["birthday"] = firstPageInfo.pbirthday.strftime('%Y-%m-%d %H:%M:%S') if firstPageInfo.pbirthday else ''
	protoItem["citizenship"] = firstPageInfo.citizenship or ''
	protoItem["chargetype"] = firstPageInfo.chargetype or ''
	protoItem["visitTimes"] = firstPageInfo.visitTimes or ''
	protoItem["age"] = str(firstPageInfo.age) if firstPageInfo.age else ''
	protoItem["babyAgeMonth"] = str(firstPageInfo.babyage_month) if firstPageInfo.babyage_month else ''
	protoItem["babyWeight"] = str(firstPageInfo.baby_weight) if firstPageInfo.baby_weight else ''
	protoItem["babyInHosWeight"] = str(firstPageInfo.baby_inhosweight) if firstPageInfo.baby_inhosweight else ''
	protoItem["bornadressProvince"] = firstPageInfo.bornadress_province or ''
	protoItem["bornadressCity"] = firstPageInfo.bornadress_city or ''
	protoItem["bornadressCounty"] = firstPageInfo.bornadress_county or ''
	protoItem["hometownProvince"] = firstPageInfo.hometown_province or ''
	protoItem["hometownCity"] = firstPageInfo.hometown_city or ''
	protoItem["nation"] = firstPageInfo.nation or ''
	protoItem["icd"] = firstPageInfo.icd or ''
	protoItem["occupation"] = firstPageInfo.occupation or ''
	protoItem["maritalStatus"] = firstPageInfo.marital_status or ''
	protoItem["nowadressProvince"] = firstPageInfo.nowadress_province or ''
	protoItem["nowadressCity"] = firstPageInfo.nowadress_city or ''
	protoItem["nowadressCounty"] = firstPageInfo.nowadress_county or ''
	protoItem["telephone"] = firstPageInfo.telephone or ''
	protoItem["nowadressPostcode"] = firstPageInfo.nowadress_postcode or ''
	protoItem["censusProvince"] = firstPageInfo.census_province or ''
	protoItem["censusCity"] = firstPageInfo.census_city or ''
	protoItem["censusCounty"] = firstPageInfo.census_county or ''
	protoItem["censusPostcode"] = firstPageInfo.census_postcode or ''
	protoItem["workAdress"] = firstPageInfo.work_adress or ''
	protoItem["workPhone"] = firstPageInfo.work_phone or ''
	protoItem["workPostcode"] = firstPageInfo.work_postcode or ''
	protoItem["concatperson"] = firstPageInfo.concatperson or ''
	protoItem["concatpersonRelation"] = firstPageInfo.concatperson_relation or ''
	protoItem["concatpersonAdress"] = firstPageInfo.concatperson_adress or ''
	protoItem["concatpersonPhone"] = firstPageInfo.concatperson_phone or ''
	protoItem["inhosWay"] = firstPageInfo.inhos_way or ''
	protoItem["admid"] = firstPageInfo.admid.strftime('%Y-%m-%d %H:%M:%S') if firstPageInfo.admid else ''
	protoItem["inhosdept"] = firstPageInfo.inhosdept or ''
	protoItem["inhosward"] = firstPageInfo.inhosward or ''
	protoItem["transferdept"] = firstPageInfo.transferdept or ''
	protoItem["discd"] = firstPageInfo.discd.strftime('%Y-%m-%d %H:%M:%S') if firstPageInfo.discd else ''
	protoItem["outhosdept"] = firstPageInfo.outhosdept or ''
	protoItem["outhosward"] = firstPageInfo.outhosward or ''
	protoItem["inhosday"] = firstPageInfo.inhosday or ''
	protoItem["pathologyNumber"] = firstPageInfo.pathology_number or ''
	protoItem["drugAllergy"] = firstPageInfo.drug_allergy or ''
	protoItem["autopsy"] = firstPageInfo.autopsy or ''
	protoItem["bloodtype"] = firstPageInfo.bloodtype or ''
	protoItem["rh"] = firstPageInfo.rh or ''
	protoItem["directorDoctor"] = firstPageInfo.director_doctor or ''
	protoItem["chiefDoctor"] = firstPageInfo.chief_doctor or ''
	protoItem["attendDoctor"] = firstPageInfo.attend_doctor or ''
	protoItem["residentDoctor"] = firstPageInfo.resident_doctor or ''
	protoItem["chargeNurse"] = firstPageInfo.charge_nurse or ''
	protoItem["physicianDoctor"] = firstPageInfo.physician_doctor or ''
	protoItem["traineeDoctor"] = firstPageInfo.trainee_doctor or ''
	protoItem["coder"] = firstPageInfo.coder or ''
	protoItem["medicalQuality"] = firstPageInfo.medical_quality or ''
	protoItem["qcDoctor"] = firstPageInfo.qc_doctor or ''
	protoItem["qcNurse"] = firstPageInfo.qc_nurse or ''
	protoItem["qcDate"] = firstPageInfo.qc_date or ''
	protoItem["leavehosType"] = firstPageInfo.leavehos_type or ''
	protoItem["againinhosplan"] = firstPageInfo.againinhosplan or ''
	protoItem["braininjurybeforeDay"] = str(firstPageInfo.braininjurybefore_day) if firstPageInfo.braininjurybefore_day else ''
	protoItem["braininjurybeforeHour"] = str(firstPageInfo.braininjurybefore_hour) if firstPageInfo.braininjurybefore_hour else ''
	protoItem["braininjurybeforeMinute"] = str(firstPageInfo.braininjurybefore_minute) if firstPageInfo.braininjurybefore_minute else ''
	protoItem["braininjuryafterDay"] = str(firstPageInfo.braininjuryafter_day) if firstPageInfo.braininjuryafter_day else ''
	protoItem["braininjuryafterHour"] = str(firstPageInfo.braininjuryafter_hour) if firstPageInfo.braininjuryafter_hour else ''
	protoItem["braininjuryafterMinute"] = str(firstPageInfo.braininjuryafter_minute) if firstPageInfo.braininjuryafter_minute else ''
	protoItem["totalcost"] = str(firstPageInfo.totalcost) if firstPageInfo.totalcost else ''
	protoItem["ownpaycost"] = str(firstPageInfo.ownpaycost) if firstPageInfo.ownpaycost else ''
	protoItem["generalcostMedicalservice"] = str(firstPageInfo.generalcost_medicalservice) if firstPageInfo.generalcost_medicalservice else ''
	protoItem["treatcostMedicalservice"] = str(firstPageInfo.treatcost_medicalservice) if firstPageInfo.treatcost_medicalservice else ''
	protoItem["nursecostMedicalservice"] = str(firstPageInfo.nursecost_medicalservice) if firstPageInfo.nursecost_medicalservice else ''
	protoItem["othercostMedicalservice"] = str(firstPageInfo.othercost_medicalservice) if firstPageInfo.othercost_medicalservice else ''
	protoItem["blcostDiagnosis"] = str(firstPageInfo.blcost_diagnosis) if firstPageInfo.blcost_diagnosis else ''
	protoItem["labcostDiagnosis"] = str(firstPageInfo.labcost_diagnosis) if firstPageInfo.labcost_diagnosis else ''
	protoItem["examcostDiagnosis"] = str(firstPageInfo.examcost_diagnosis) if firstPageInfo.examcost_diagnosis else ''
	protoItem["clinicalcostDiagnosis"] = str(firstPageInfo.clinicalcost_diagnosis) if firstPageInfo.clinicalcost_diagnosis else ''
	protoItem["noopscostTreat"] = str(firstPageInfo.noopscost_treat) if firstPageInfo.noopscost_treat else ''
	protoItem["clinicalcostTreat"] = str(firstPageInfo.clinicalcost_treat) if firstPageInfo.clinicalcost_treat else ''
	protoItem["opscostTreat"] = str(firstPageInfo.opscost_treat) if firstPageInfo.opscost_treat else ''
	protoItem["anesthesiacostTreat"] = str(firstPageInfo.anesthesiacost_treat) if firstPageInfo.anesthesiacost_treat else ''
	protoItem["surgicacostTrear"] = str(firstPageInfo.surgicacost_trear) if firstPageInfo.surgicacost_trear else ''
	protoItem["kfcost"] = str(firstPageInfo.kfcost) if firstPageInfo.kfcost else ''
	protoItem["cmtreatcost"] = str(firstPageInfo.cmtreatcost) if firstPageInfo.cmtreatcost else ''
	protoItem["wmmedicine"] = str(firstPageInfo.wmmedicine) if firstPageInfo.wmmedicine else ''
	protoItem["antibacterial"] = str(firstPageInfo.antibacterial) if firstPageInfo.antibacterial else ''
	protoItem["medicineCpm"] = str(firstPageInfo.medicine_cpm) if firstPageInfo.medicine_cpm else ''
	protoItem["medicineChm"] = str(firstPageInfo.medicine_chm) if firstPageInfo.medicine_chm else ''
	protoItem["bloodcost"] = str(firstPageInfo.bloodcost) if firstPageInfo.bloodcost else ''
	protoItem["productcostBdb"] = str(firstPageInfo.productcost_bdb) if firstPageInfo.productcost_bdb else ''
	protoItem["productcostQdb"] = str(firstPageInfo.productcost_qdb) if firstPageInfo.productcost_qdb else ''
	protoItem["productcostNxyz"] = str(firstPageInfo.productcost_nxyz) if firstPageInfo.productcost_nxyz else ''
	protoItem["productcostXbyz"] = str(firstPageInfo.productcost_xbyz) if firstPageInfo.productcost_xbyz else ''
	protoItem["consumablesExam"] = str(firstPageInfo.consumables_exam) if firstPageInfo.consumables_exam else ''
	protoItem["consumablesTreat"] = str(firstPageInfo.consumables_treat) if firstPageInfo.consumables_treat else ''
	protoItem["consumablesOps"] = str(firstPageInfo.consumables_ops) if firstPageInfo.consumables_ops else ''
	protoItem["othercost"] = str(firstPageInfo.othercost) if firstPageInfo.othercost else ''

def unmarshalTemperatureInfo(protoItem, temperatureInfo):
	protoItem["id"] = temperatureInfo.id or ''
	protoItem["name"] = temperatureInfo.item_name or ''
	protoItem["value"] = temperatureInfo.value or ''
	protoItem["unit"] = temperatureInfo.unit or ''
	protoItem["time"] = temperatureInfo.time.strftime('%Y-%m-%d %H:%M:%S') if temperatureInfo.time else ''

def unmarshalDiagnosisInfo(protoItem, diagnosisInfo):
	protoItem["id"] = str(diagnosisInfo.id) or ''
	protoItem["diagId"] = diagnosisInfo.diagId or ''
	protoItem["code"] = diagnosisInfo.code or ''
	protoItem["name"] = diagnosisInfo.name or ''
	protoItem["type"] = diagnosisInfo.type
	protoItem["mainFlag"] = diagnosisInfo.mainFlag or ''
	protoItem["diagTime"] = diagnosisInfo.diagtime.strftime('%Y-%m-%d %H:%M:%S') if diagnosisInfo.diagtime else ''

def unmarshalCaseLabExamInfo(response, caseinfo, firstpageInfo,temperatureInfo=[],diagnosisInfo=[], emrinfo=[], medicalAdvice=[], assayList=[], examList=[], part=0):
	caseinfoItem = response["basicInfo"]
	unmarshalCaseInfo(caseinfo, caseinfoItem, 'hosipital')
	if firstpageInfo:
		firstpageItem = response["firstPageInfo"]
		unmarshalFirstPageInfo(firstpageItem, firstpageInfo)
	if temperatureInfo:
		for info in temperatureInfo:
			protoItem = {}  # response.TemperatureInfo.add()
			unmarshalTemperatureInfo(protoItem, info)
			response["TemperatureInfo"].append(protoItem)
	if diagnosisInfo:
		for info in diagnosisInfo:
			protoItem = {}  # response.DiagnosisInfo.add()
			unmarshalDiagnosisInfo(protoItem, info)
			response["DiagnosisInfo"].append(protoItem)
	if (part == 1 or part == 0) and emrinfo:
		for emr in emrinfo:
			emrItem = {}  # response.emrInfo.add()
			htmlContent = {}
			xmlContents = {}
			if emr.emrContentId:
				htmlContent[emr.getEmrContentId()] = emr.getEmrHtml()
				xmlContents[emr.getEmrContentId()] = emr.getEmrContents()
			unmarshalCaseEmr(emr, htmlContent, emrItem, xmlContents)
			response["emrInfo"].append(emrItem)
	if (part == 2 or part == 0) and medicalAdvice:
		for order in medicalAdvice:
			orderItem = {}  # response.medicaladviceInfo.add()
			unmarshalMedicalAdvice(order, orderItem, True)
			response["medicaladviceInfo"].append(orderItem)
	if (part == 3 or part == 0) and assayList:
		for assay in assayList:
			assayItem = {}  # response.assayresultInfo.add()
			unmarshalAssay(assay, assayItem)
			response["assayresultInfo"].append(assayItem)
	if (part == 4 or part == 0) and examList:
		for exam in examList:
			examItem = {}  # response.examinationInfo.add()
			unmarshalExamination(exam, examItem)
			response["examinationInfo"].append(examItem)


def unmarshalProblemSumTags(tagProto, sumTags: ProblemSumTags):
	for tag in sumTags.get_sum_tags():
		tagItem = {}  # tagProto.add()
		tagItem["name"] = tag.get('name', '-')
		tagItem["value"] = tag.get('value', '-')
		tagItem["count"] = tag.get('count', 0)
		tagProto.append(tagItem)


def unmarshalLabReport(report, protoItem):
	if not report:
		return
	# 化验报告单基本信息
	protoItem["reportId"]= report.getReportId()
	protoItem["reportName"]= report.testname or ''
	protoItem["specimen"]= report.specimen or ''
	protoItem["requestTime"]= report.requestTime.strftime('%Y-%m-%d %H:%M:%S') if report.requestTime else ''
	protoItem["reportTime"]= report.reportTime.strftime('%Y-%m-%d %H:%M:%S') if report.reportTime else ''
	protoItem["requestDept"]= report.requestDepartment or ''
	protoItem["requestDoctor"]= report.requestDoctor or ''
	if report.contents:
		# 化验项目结果
		for content in report.contents:
			subItem = {}  # protoItem.items.add()
			subItem["id"]= content.id
			subItem["itemname"]= content.itemname or ''
			subItem["result"]= content.result or ''
			subItem["unit"]= content.unit or ''
			subItem["abnormal"]= content.resultFlag or ''
			subItem["valrange"]= content.valrange or ''
			subItem["abnormalIcon"]= LAB_ABNORMAL_ICON.get(content.resultFlag) or ''
			protoItem["items"].append(subItem)

def unmarshalExamReport(exam, protoItem):
	if not exam:
		return
	# 化验报告单基本信息
	protoItem.reportId = exam.getReportId()
	protoItem.examName = exam.examname or ''
	protoItem.examType = exam.examtype or ''
	protoItem.position = exam.position or ''
	protoItem.requestTime = exam.requestTime.strftime('%Y-%m-%d %H:%M:%S') if exam.requestTime else ''
	protoItem.reportTime = exam.reportTime.strftime('%Y-%m-%d %H:%M:%S') if exam.reportTime else ''
	protoItem.requestDepartment = exam.requestDepartment or ''
	protoItem.requestDoctor = exam.requestDoctor or ''
	protoItem.reviewDoctor = exam.reviewDoctor or ''
	protoItem.execDepartment = exam.execDepartment or ''
	protoItem.execDoctor = exam.execDoctor or ''
	if exam.contents:
		# 化验项目结果
		for content in exam.contents:
			subItem = protoItem.items.add()
			subItem.id = content.id
			subItem.itemname = content.itemname or ''
			subItem.desc = content.description or ''
			subItem.result = content.result or ''


def unmarshalfpdiagnosis(fpdiagnosis, protoItem):
	if not fpdiagnosis:
		return
	protoItem.code = fpdiagnosis.icdcode or ''
	protoItem.name = fpdiagnosis.icdname or ''
	protoItem.typeCode = fpdiagnosis.typecode or ''
	protoItem.typeName = fpdiagnosis.typename or ''
	protoItem.inCondition = fpdiagnosis.incondition or ''
	protoItem.prognosis = fpdiagnosis.prognosis or ''
	protoItem.diagTime = fpdiagnosis.diagtime.strftime('%Y-%m-%d %H:%M:%S') if fpdiagnosis.diagtime else ''
	protoItem.dateModified = fpdiagnosis.datemodified.strftime('%Y-%m-%d %H:%M:%S') if fpdiagnosis.datemodified else ''
	protoItem.diagNumber = fpdiagnosis.diagnumber or ''
	protoItem.diagDoctor = fpdiagnosis.diagdoctor or ''


def unmarshalfpoperation(fpoperation, protoItem):
	if not fpoperation:
		return
	protoItem.operClass = fpoperation.oper_class or ''
	protoItem.operNo = fpoperation.oper_no or ''
	protoItem.operCode = fpoperation.oper_code or ''
	protoItem.operName = fpoperation.oper_name or ''
	protoItem.operLevel = fpoperation.oper_level or ''
	protoItem.assistant1 = fpoperation.assistant_1 or ''
	protoItem.assistant2 = fpoperation.assistant_2 or ''
	protoItem.cutLevel = fpoperation.cut_level or ''
	protoItem.aneMethod = fpoperation.ane_method or ''
	protoItem.healLevel = fpoperation.heal_level or ''
	protoItem.dateModified = fpoperation.datemodified.strftime('%Y-%m-%d %H:%M:%S') if fpoperation.datemodified else ''

def unmarshalpathology(pathology, protoItem):
	protoItem.table = pathology.table or ''
	protoItem.key = pathology.key or ''
	protoItem.data = pathology.data or ''
	protoItem.createTime = pathology.createTime.strftime('%Y-%m-%d %H:%M:%S') if pathology.createTime else ''

def unmarshaldiseaseStatsDepartment(result, response, target, department):
	if target == '覆盖病种数' or (department != '' and department != '全部科室'):
		protoItem = response.department.add()
		protoItem.name = target or ''
		for item in result:
			proto = protoItem.items.add()
			proto["key"] = item['name']
			proto["value"] = str(item['num'])
	else:
		protoItemDisease = response.department.add()
		protoItemAllCase = response.department.add()
		protoItemDisease.name = '单病种'
		protoItemAllCase.name = '全部患者'
		for item in result:
			protoDisease = protoItemDisease.items.add()
			protoAllCase = protoItemAllCase.items.add()
			protoDisease.key = item['name']
			protoAllCase.key = item['name']
			protoDisease.value = str(item['num'])
			protoAllCase.value = str(item['allCase'])

def unmarshaldiseaseStatsTrend(result, response, target, front_year=0):
	t = '-本期' if not front_year else '-同期'
	if target == '覆盖病种数':
		protoItem = response.trend.add()
		protoItem.name = '单病种' + t
		for item in result:
			proto = protoItem.items.add()
			proto["key"] = item['time']
			proto["value"] = str(item['num'])
	else:
		protoItemDisease = response.trend.add()
		protoItemAllCase = response.trend.add()
		protoItemDisease.name = '单病种' + t
		protoItemAllCase.name = '全部患者' + t
		for item in result:
			protoDiease = protoItemDisease.items.add()
			protoAllCase = protoItemAllCase.items.add()
			protoDiease.key = item['time']
			protoDiease.value = str(item['num'])
			protoAllCase.key = item['time']
			protoAllCase.value = str(item['allCase'])


def unmarshaldiseaseContrastRadar(result: Dict, response):
	for key, value in result.items():
		protoItem = response.radar.add()
		protoItem.name = key
		for k, v in value.items():
			proto = protoItem.items.add()
			proto["key"] = k
			proto["value"] = str(v)

def unmarshaldiseaseContrastTrend(result: Dict, response):
	for key, value in result.items():
		protoItem = response.trend.add()
		protoItem.name = key
		for k, v in value.items():
			proto = protoItem.data.add()
			proto["name"] = k
			for _k, _v in v.items():
				p = proto.items.add()
				p.key = _k
				p.value = _v


def getActiveProblemStatus(no_fix_num, num):
	"""
	根据问题数判断当前事中人工问题状态
	:return:
	"""
	if not no_fix_num:
		no_fix_num = 0
	if not num:
		num = 0
	if num == 0:
		return "无问题"
	elif no_fix_num > 0 and no_fix_num == num:
		return "未整改"
	elif 0 < no_fix_num < num:
		return "部分整改"
	elif no_fix_num == 0 and num > 0:
		return "全部整改"


def unmarshalProblemRecordList(protoItem, item):
	protoItem["qcItemId"]= str(item.qcItemId or 0)
	reason = item.reason if item.reason != "0" and item.reason else "缺失文书"
	protoItem["reason"]= reason
	protoItem["docType"]= item.standard_emr or ""
	protoItem["problemType"]= QCITEM_CATEGORY.get(item.category) or ""
	protoItem["problemStatus"]= "现存" if item.existFlag == 1 else "已解决"
	protoItem["auditType"]= item.auditType


def unmarshalProblemRecordDetail(protoItem, item):
	protoItem["auditType"]= item.auditType or ""
	protoItem["action"]= item.action or ""
	protoItem["actionType"]= getActionType(item.action)
	protoItem["time"]= item.create_time.strftime('%Y-%m-%d %H:%M') if item.create_time else ""
	protoItem["doctor"]= item.doctor_name or ""


def getActionType(action):
	action_dict = {"提出问题": "apply", "确认解决": "pass", "医生整改完成": "pass", "发送问题": "apply", "退回返修": "refuse"}
	return action_dict.get(action, "apply")


def unmarshalSampleDetail(protoItem, x, request, caseTagDict):
	"""序列化抽取详情
	"""
	protoItem["id"]= x.model.id
	protoItem["caseId"]= x.model.caseId
	protoItem["sampleId"]= x.model.recordId
	protoItem["patientId"]= x.caseModel.inpNo or x.caseModel.patientId
	protoItem["visitTimes"]= x.caseModel.visitTimes if x.caseModel.visitTimes else 0
	protoItem["name"]= x.caseModel.name if x.caseModel.name else ""
	protoItem["age"]= str(x.caseModel.age) if x.caseModel.age else ""
	protoItem["gender"]= x.caseModel.gender if x.caseModel.gender else ""
	protoItem["branch"]= x.caseModel.branch if x.caseModel.branch else ""
	protoItem["ward"]= x.caseModel.wardName if x.caseModel.wardName else ""
	protoItem["group"]= x.caseModel.medicalGroupName or ""
	protoItem["attendDoctor"]= x.caseModel.attendDoctor if x.caseModel.attendDoctor else ""
	protoItem["admitTime"]= x.caseModel.admitTime.strftime('%Y-%m-%d') if x.caseModel.admitTime else ""
	protoItem["dischargeTime"]= x.caseModel.dischargeTime.strftime('%Y-%m-%d') if x.caseModel.dischargeTime else ""
	protoItem["dischargeDept"]= x.caseModel.outDeptName if x.caseModel.outDeptName else ""
	protoItem["department"]= x.caseModel.outDeptName or x.caseModel.department or ""
	ar_status = getattr(x.auditRecord, AuditRecord.getOperatorFields(auditType=request.auditType).statusField)
	protoItem["status"]= ar_status or 0
	protoItem["inpDays"]= x.caseModel.inpDays if x.caseModel.inpDays else 0
	protoItem["problemCount"]= AuditRecord(x.auditRecord).getProblemCount(request.auditType) if x.auditRecord else 0
	ar_reviewer = getattr(x.auditRecord,
							AuditRecord.getOperatorFields(auditType=request.auditType).reviewerNameField)
	ar_review_time = getattr(x.auditRecord,
								AuditRecord.getOperatorFields(auditType=request.auditType).reviewTimeField)
	protoItem["distributeDoctor"]= x.model.expertName if x.model.expertName else ""
	protoItem["reviewer"]= ar_reviewer or ""
	protoItem["reviewTime"]= ar_review_time.strftime('%Y-%m-%d %H:%M:%S') if ar_review_time else ""
	if x.caseModel.tags:
		for tag in x.caseModel.tags:
			protoItemTag = {}  # protoItem.caseTags.add()
			t = caseTagDict.get(tag) if caseTagDict else None
			protoItemTag["name"] = t.name if t else ""
			protoItemTag["code"] = t.code if t else tag
			protoItemTag["icon"] = t.icon if t else ""

	caseScore = AuditRecord(x.auditRecord).getScore(request.auditType) if x.auditRecord else 100.0
	if not caseScore:
		caseScore = 100.0
	caseRating = "甲" if caseScore >= 90 else "乙"
	protoItem["caseRating"]= "丙" if caseScore < 80 else caseRating
	protoItem["caseScore"]= '{:g}'.format(caseScore)


def cCateItem(protoModel, qciModel):
	# 质控点信息
	if not qciModel:
		return
	protoModel["id"] = qciModel.id
	protoModel["categoryId"] = qciModel.categoryId
	protoModel["itemId"] = str(qciModel.itemId)
	protoModel["name"] = qciModel.qcItemModel.requirement if qciModel.qcItemModel else ''
	protoModel["maxScore"] = qciModel.maxScore
	protoModel["score"] = qciModel.score


def unmarshalDoctorArchivingRateCase(protoItem, item):
	protoItem["id"] = item[0] if item[0] else ""
	protoItem["caseId"] = item[1] if item[1] else ""
	protoItem["patientId"] = item[2] if item[2] else ""
	protoItem["name"] = item[3] if item[3] else ""
	protoItem["gender"] = item[4] if item[4] else ""
	protoItem["hospital"] = item[5] if item[5] else ""
	protoItem["branch"] = item[6] if item[6] else ""
	protoItem["department"] = item[7] if item[7] else ""
	protoItem["attendDoctor"] = item[8] if item[8] else ""
	protoItem["admitTime"] = item[9].strftime("%Y-%m-%d") if item[9] else ""
	protoItem["dischargeTime"] = item[10].strftime("%Y-%m-%d") if item[10] else ""

	protoItem["inpDays"] = int(item[12]) if item[12] else 0
	protoItem["applyFlag"] = item[13] if item[13] else ""
	protoItem["applyTime"] = item[14].strftime("%Y-%m-%d") if item[14] else ""
	protoItem["applyDoctor"] = item[15] if item[15] else ""
	protoItem["reviewFlag"] = item[16] if item[16] else ""
	protoItem["reviewer"] = item[17] if item[17] else ""
	protoItem["reviewTime"] = item[18].strftime("%Y-%m-%d") if item[18] else ""
	if item[19] and item[19] == 1:
		protoItem["isDead"] = '死亡'
	else:
		protoItem["isDead"] = '未亡'

	protoItem["isSecondArchiving"] = item[20] if item[20] else ""
	protoItem["isThirdArchiving"] = item[21] if item[21] else ""
	protoItem["isSeventhArchiving"] = item[22] if item[22] else ""
	# 此标记表示没有出院科室问题，使用反了，故此处bool取反
	protoItem["hasDischargeDeptProblem"] = False if item[23] else True

	protoItem["isPrimaryDiagValid"] = item[24] if item[24] else ""
	protoItem["isMinorDiagValid"] = item[25] if item[25] else ""
	protoItem["isPrimaryOperValid"] = item[26] if item[26] else ""
	protoItem["isMinorOperValid"] = item[27] if item[27] else ""

	if item[16] == "已退回":
		# 只有已退回状态的才显示审核说明
		# protoItem["reviewDetail"] = item[28] if item[28] else ""
		protoItem["reviewDetail"] = ""
	else:
		protoItem["reviewDetail"] = ""


def unmarshalOperation(protoItem, info):
	protoItem["id"] = info.model.id or 0
	protoItem["type"] = info.model.type or ''
	protoItem["code"] = info.model.code or ''
	protoItem["operation"] = info.model.name or ''
	protoItem["originOperation"] = info.model.originName or ''
	protoItem["operator"] = info.operator or ''
	protoItem["helperOne"] = info.helperOne or ''
	protoItem["helperTwo"] = info.helperTwo or ''
	protoItem["narcosis"] = info.model.narcosis or ''
	protoItem["narcosisDoctor"] = info.narcosisDoctor or ''
	protoItem["cut"] = info.model.cut or ''
	protoItem["healLevel"] = info.healLevel or ''
	protoItem["level"] = info.model.level or ''
	protoItem["operationTime"] = info.model.operation_time.strftime("%Y-%m-%d") if info.model.operation_time else ""

def unmarshalCodeInfo(protoItem, info):
	protoItem["code"] = info.code or ''
	protoItem["name"] = info.name or ''
	if hasattr(info, "type"):
		protoItem["type"] = info.type or ''


def unmarshalOriginCodeInfo(protoItem, info):
	protoItem["code"] = info.icdcode or ''
	protoItem["name"] = info.icdname or ''

def unmarshalOriginOperCodeInfo(protoItem, info):
	protoItem["code"] = info.oper_code or ''
	protoItem["name"] = info.oper_name or ''

def unmarshal_diagnosis_info(proto, diagnosis_info):
	proto["isPrimary"] = "主诊断" if diagnosis_info.isPrimary else ""
	proto["code"] = diagnosis_info.code or ""
	proto["diagnosis"] = diagnosis_info.name or ""
	proto["originDiagnosis"] = diagnosis_info.originName or ""
	proto["situation"] = diagnosis_info.situation or ""
	proto["returnTo"] = diagnosis_info.returnTo or ""
	proto["id"] = diagnosis_info.id

def unmarshalCaseInfo(proto, info):
	proto["id"] = info.id or 0
	proto["caseId"] = info.caseId or ''
	proto["patientId"] = info.patientId or ''
	proto["name"] = info.name or ''
	proto["branch"] = info.branch or ''
	proto["ward"] = info.wardName or ''
	proto["department"] = info.outDeptName or info.department or ''
	proto["attendDoctor"] = info.attendDoctor or ''
	proto["dischargeTime"] = info.dischargeTime.strftime('%Y-%m-%d') if info.dischargeTime else ''
	proto["admitTime"] = info.admitTime.strftime('%Y-%m-%d') if info.admitTime else ''
	proto["codeStatus"] = "已编码" if info.codeStatus else "未编码"
	if info.dischargeTime:
		proto["inpDays"] = info.inpDays or 0
	else:
		proto["inpDays"] = (datetime.now() - info.admitTime).days
	if info.audit_record:
		proto["status"] = parseStatus(False, 'fpStatus')
		proto["statusName"] = parseStatusName(False, 'fpStatus')
		proto["problemCount"] = info.audit_record.fpProblemCount or 0
		proto["score"] = "{:g}".format(info.audit_record.fpScore or 100)
	if fp_info := info.fp_info:
		proto["codeDoctor"] = fp_info.coder or ''
		proto["codeTime"] = fp_info.code_time.strftime('%Y-%m-%d') if fp_info.code_time else ''
	if info.TagsModel:
		for tag in info.TagsModel:
			tagItem = {}  # proto.caseTags.add()
			tagItem["name"] = tag.name or ""
			tagItem["code"] = tag.code
			tagItem["icon"] = tag.icon.decode() or ""
			proto["caseTags"].append(tagItem)

def setRequestStatus(reqObj):
	"""
	首页节点状态获取
	:return:
	"""
	reqObj['status'] = []
	for s in AUDIT_STATUS:
		if s.get('hideflag'):
			continue
		if s.get('filter'):
			reqObj['status'].extend(s.get('filter'))

