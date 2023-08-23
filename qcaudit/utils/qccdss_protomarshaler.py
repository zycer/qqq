from qcaudit.common.const import AUDIT_STATUS, RECHECK_STATUS, CASE_STATUS_ARCHIVED, CASE_STATUS_REFUSED, \
	CASE_STATUS_APPLIED, CASE_STATUS_NOTAPPLIED, LAB_ABNORMAL_ICON
from qcaudit.domain.audit.auditrecord import AuditRecord
from google.protobuf.json_format import MessageToDict
from datetime import datetime
import re

lab_result_flag_dict = {
	'超出正常': '高于正常',
	'HighLimit': '高于正常',
	'H': '高于正常',
	'低于正常': '低于正常',
	'LowLimit': '低于正常',
	'L': '低于正常',
}

re_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAWCAYAAADafVyIAAAAAXNSR0IArs4c6QAAAoVJREFUSEvtlUtIVFEYx//n3Llzx2fjqJWv1LEp0EBRyh6SKAZGSQ4TuBBqUzuDgnJTqzLcRAQ9bRGRq4IKkiwsBlSihRZKExnMlGYEvTBHo5n7OnHPNDOOo02E7vxWh++ee37n//++j0O8B5IYljHICiCRu0tqkaoDGgMkIYolT5strMujJLoI/95WLiIvhfD12WEFldkUuwujp3WPqRj9puNcjTlyHrndKLGTz2W0V4k82T2modRGULWaxkDPDCm4XGtGqS2UP9IvoyaXosVhiuxbFHBxVMHNXRJ63ms4Nijzw3OSCZdLCHC0QkT7Mxmnq8X/B2xZK+C+T4XKgEu1ZqxJJjg+KKN4FcWpzSJaHgfjAAOfNFiEkGVGBDSGnwqQaQnlyrMouEWGguYSE+ryKTzfGQ4+CfJNDQUCOraJMLbvfxQLaOuXuZo9RXMqOq+SZooQoPOFAqddgPujjuEvGpqKTchNIegd1zA5q6M2T8CEn6Fze9Siw24ZjYUCXCWLAwweB5wfUVCRRbn393yGbMBhpXBYCYrSKcb9Oq68UmMsau0LwvuDITspalFYwLU6M/JTQ/mIRUaRfdOM+/hhhuHtlI7JWcZbbiGLqu8EcKJS5JeYG67eIPqaLbCnzwNcrZPgfBiAd5qhII2gzEaxwUqxKZOgPl+IqcGbKR1NPUG8bk2KGSoDtP7Wr3jAhREFNxqkUCeoDO/8jIMMFRkSwaEyE++ijq0iNmZQvrZJBNfrowMVVrEgwPjhX+LBXgkTM4wPmdtpwbq0eP/jAAMuCxv6rGOf/e/dcNenYWcuRapI8PKrjh05sZMevmCXR0WLQ4BV+lODlfcgUe2W9D1YCLbsgN+jMBjLamiCsgAAAABJRU5ErkJggg=='

def parseGender(gender):
	if not gender:
		return ""
	if gender == "F" or gender == "f":
		gender = "女"
	elif gender == "M" or gender == "m":
		gender = "男"
	return gender


def QCunmarshalCaseInfo(caseInfo, protoItem, auditType, department_dict):
	"""病历基本信息转换
	"""
	if not caseInfo:
		return
	protoItem["id"] = caseInfo.id or 0
	protoItem["caseId"] = caseInfo.caseId or ""
	protoItem["patientId"] = caseInfo.patientId or ""
	protoItem["name"] = caseInfo.name or ""
	protoItem["gender"] = parseGender(caseInfo.gender)
	protoItem["age"] = f'{caseInfo.age or ""}{caseInfo.ageUnit or ""}'
	protoItem["hospital"] = caseInfo.hospital or ""
	protoItem["branch"] = caseInfo.branch or ""
	protoItem["attendDoctor"] = caseInfo.attendDoctor or ""
	protoItem["admitTime"] = caseInfo.admitTime.strftime('%Y-%m-%d') if caseInfo.admitTime else ""
	protoItem["dischargeTime"] = caseInfo.dischargeTime.strftime('%Y-%m-%d') if caseInfo.dischargeTime else ""
	protoItem["status"] = caseInfo.status or 0
	if caseInfo.dischargeTime:
		protoItem["inpDays"] = caseInfo.inpDays or 0
		if caseInfo.status == CASE_STATUS_ARCHIVED:
			protoItem["caseType"] = "archive"
		else:
			protoItem["caseType"] = 'final'
	else:
		protoItem["caseType"] = 'active'
		protoItem["inpDays"] = (datetime.now() - caseInfo.admitTime).days
	if protoItem["inpDays"] <= 0:
		protoItem["inpDays"] = 1

	protoItem["applyTime"] = caseInfo.applyTime.strftime('%Y-%m-%d') if caseInfo.applyTime else ""
	protoItem["applyDoctor"] = caseInfo.applyDoctor or ""
	protoItem["isDead"] = "死亡" if caseInfo.isDead else "未死亡"
	protoItem["visitTimes"] = caseInfo.visitTimes or 0
	protoItem["autoReviewFlag"] = caseInfo.autoReviewFlag or 0
	protoItem["diagnosis"] = caseInfo.diagnosis or ""
	protoItem["wardName"] = caseInfo.wardName or ""
	protoItem["bedId"] = caseInfo.bedId or ""
	protoItem["dischargeDept"] = caseInfo.outDeptName or ""
	protoItem["inDepartment"] = caseInfo.department or ""
	protoItem["department"] = protoItem["dischargeDept"] or caseInfo.department or ""
	protoItem["refuseCount"] = caseInfo.refuseCount or 0
	protoItem["auditType"] = auditType
	protoItem["lastUpdateTime"] = caseInfo.updateTime.strftime('%Y-%m-%d %H:%M:%S') if caseInfo.updateTime else ""
	protoItem["operationTimes"] = caseInfo.oper_count or 0
	# if caseInfo.TagsModel:
	# 	for tag in caseInfo.TagsModel:
	# 		tagItem = protoItem.caseTags.add()
	# 		tagItem.name = tag.name or ""
	# 		tagItem.code = tag.code
	# 		tagItem.icon = tag.icon or ""
	if item := department_dict.get(caseInfo.departmentId, None):
		protoItem["std_name"] = item.std_name or ''
		protoItem["std_code"] = item.std_code or ''


def QCunmarshalFirstPageInfo(protoItem, firstPageInfo):
	if not firstPageInfo:
		return
	protoItem["id"] = firstPageInfo.id or ''
	protoItem["caseId"] = firstPageInfo.caseId or ''
	protoItem["patientId"] = firstPageInfo.patientId or ''
	protoItem["pname"] = firstPageInfo.pname or ''
	protoItem["psex"] = firstPageInfo.psex or ''
	protoItem["pbirthday"] = firstPageInfo.pbirthday.strftime('%Y-%m-%d %H:%M:%S') if firstPageInfo.pbirthday else ''
	protoItem["citizenship"] = firstPageInfo.citizenship or ''
	protoItem["chargetype"] = firstPageInfo.chargetype or ''
	protoItem["visitTimes"] = firstPageInfo.visitTimes or ''
	protoItem["age"] = str(firstPageInfo.age) if firstPageInfo.age else ''
	protoItem["babyage_month"] = str(firstPageInfo.babyage_month) if firstPageInfo.babyage_month else ''
	protoItem["baby_weight"] = str(firstPageInfo.baby_weight) if firstPageInfo.baby_weight else ''
	protoItem["baby_inhosweight"] = str(firstPageInfo.baby_inhosweight) if firstPageInfo.baby_inhosweight else ''
	protoItem["bornadress_province"] = firstPageInfo.bornadress_province or ''
	protoItem["bornadress_city"] = firstPageInfo.bornadress_city or ''
	protoItem["bornadress_county"] = firstPageInfo.bornadress_county or ''
	protoItem["hometown_province"] = firstPageInfo.hometown_province or ''
	protoItem["hometown_city"] = firstPageInfo.hometown_city or ''
	protoItem["nation"] = firstPageInfo.nation or ''
	protoItem["icd"] = firstPageInfo.icd or ''
	protoItem["occupation"] = firstPageInfo.occupation or ''
	protoItem["marital_status"] = firstPageInfo.marital_status or ''
	protoItem["nowadress_province"] = firstPageInfo.nowadress_province or ''
	protoItem["nowadress_city"] = firstPageInfo.nowadress_city or ''
	protoItem["nowadress_county"] = firstPageInfo.nowadress_county or ''
	protoItem["telephone"] = firstPageInfo.telephone or ''
	protoItem["nowadress_postcode"] = firstPageInfo.nowadress_postcode or ''
	protoItem["census_province"] = firstPageInfo.census_province or ''
	protoItem["census_city"] = firstPageInfo.census_city or ''
	protoItem["census_county"] = firstPageInfo.census_county or ''
	protoItem["census_postcode"] = firstPageInfo.census_postcode or ''
	protoItem["work_adress"] = firstPageInfo.work_adress or ''
	protoItem["work_phone"] = firstPageInfo.work_phone or ''
	protoItem["work_postcode"] = firstPageInfo.work_postcode or ''
	protoItem["concatperson"] = firstPageInfo.concatperson or ''
	protoItem["concatperson_relation"] = firstPageInfo.concatperson_relation or ''
	protoItem["concatperson_adress"] = firstPageInfo.concatperson_adress or ''
	protoItem["concatperson_phone"] = firstPageInfo.concatperson_phone or ''
	protoItem["inhos_way"] = firstPageInfo.inhos_way or ''
	protoItem["admid"] = firstPageInfo.admid.strftime('%Y-%m-%d %H:%M:%S') if firstPageInfo.admid else ''
	protoItem["inhosdept"] = firstPageInfo.inhosdept or ''
	protoItem["inhosward"] = firstPageInfo.inhosward or ''
	protoItem["transferdept"] = firstPageInfo.transferdept or ''
	protoItem["discd"] = firstPageInfo.discd.strftime('%Y-%m-%d %H:%M:%S') if firstPageInfo.discd else ''
	protoItem["outhosdept"] = firstPageInfo.outhosdept or ''
	protoItem["outhosward"] = firstPageInfo.outhosward or ''
	protoItem["inhosday"] = firstPageInfo.inhosday or ''
	protoItem["pathology_number"] = firstPageInfo.pathology_number or ''
	protoItem["drug_allergy"] = firstPageInfo.drug_allergy or ''
	protoItem["autopsy"] = firstPageInfo.autopsy or ''
	protoItem["bloodtype"] = firstPageInfo.bloodtype or ''
	protoItem["rh"] = firstPageInfo.rh or ''
	protoItem["director_doctor"] = firstPageInfo.director_doctor or ''
	protoItem["chief_doctor"] = firstPageInfo.chief_doctor or ''
	protoItem["attend_doctor"] = firstPageInfo.attend_doctor or ''
	protoItem["resident_doctor"] = firstPageInfo.resident_doctor or ''
	protoItem["charge_nurse"] = firstPageInfo.charge_nurse or ''
	protoItem["physician_doctor"] = firstPageInfo.physician_doctor or ''
	protoItem["trainee_doctor"] = firstPageInfo.trainee_doctor or ''
	protoItem["coder"] = firstPageInfo.coder or ''
	protoItem["medical_quality"] = firstPageInfo.medical_quality or ''
	protoItem["qc_doctor"] = firstPageInfo.qc_doctor or ''
	protoItem["qc_nurse"] = firstPageInfo.qc_nurse or ''
	protoItem["qc_date"] = firstPageInfo.qc_date or ''
	protoItem["leavehos_type"] = firstPageInfo.leavehos_type or ''
	protoItem["againinhosplan"] = firstPageInfo.againinhosplan or ''
	protoItem["braininjurybefore_day"] = str(
		firstPageInfo.braininjurybefore_day) if firstPageInfo.braininjurybefore_day or firstPageInfo.braininjurybefore_day == 0 else ''
	protoItem["braininjurybefore_hour"] = str(
		firstPageInfo.braininjurybefore_hour) if firstPageInfo.braininjurybefore_hour or firstPageInfo.braininjurybefore_hour == 0 else ''
	protoItem["braininjurybefore_minute"] = str(
		firstPageInfo.braininjurybefore_minute) if firstPageInfo.braininjurybefore_minute or firstPageInfo.braininjurybefore_minute == 0 else ''
	protoItem["braininjuryafter_day"] = str(
		firstPageInfo.braininjuryafter_day) if firstPageInfo.braininjuryafter_day or firstPageInfo.braininjuryafter_day == 0 else ''
	protoItem["braininjuryafter_hour"] = str(
		firstPageInfo.braininjuryafter_hour) if firstPageInfo.braininjuryafter_hour or firstPageInfo.braininjuryafter_hour == 0 else ''
	protoItem["braininjuryafter_minute"] = str(
		firstPageInfo.braininjuryafter_minute) if firstPageInfo.braininjuryafter_minute or firstPageInfo.braininjuryafter_minute == 0 else ''
	protoItem["totalcost"] = str(firstPageInfo.totalcost) if firstPageInfo.totalcost != None else ''
	protoItem["ownpaycost"] = str(firstPageInfo.ownpaycost) if firstPageInfo.ownpaycost != None else ''
	protoItem["generalcost_medicalservice"] = str(
		firstPageInfo.generalcost_medicalservice) if firstPageInfo.generalcost_medicalservice != None else ''
	protoItem["treatcost_medicalservice"] = str(
		firstPageInfo.treatcost_medicalservice) if firstPageInfo.treatcost_medicalservice != None else ''
	protoItem["nursecost_medicalservice"] = str(
		firstPageInfo.nursecost_medicalservice) if firstPageInfo.nursecost_medicalservice != None else ''
	protoItem["othercost_medicalservice"] = str(
		firstPageInfo.othercost_medicalservice) if firstPageInfo.othercost_medicalservice != None else ''
	protoItem["blcost_diagnosis"] = str(firstPageInfo.blcost_diagnosis) if firstPageInfo.blcost_diagnosis else ''
	protoItem["labcost_diagnosis"] = str(firstPageInfo.labcost_diagnosis) if firstPageInfo.labcost_diagnosis else ''
	protoItem["examcost_diagnosis"] = str(firstPageInfo.examcost_diagnosis) if firstPageInfo.examcost_diagnosis else ''
	protoItem["clinicalcost_diagnosis"] = str(
		firstPageInfo.clinicalcost_diagnosis) if firstPageInfo.clinicalcost_diagnosis else ''
	protoItem["noopscost_treat"] = str(firstPageInfo.noopscost_treat) if firstPageInfo.noopscost_treat else ''
	protoItem["clinicalcost_treat"] = str(firstPageInfo.clinicalcost_treat) if firstPageInfo.clinicalcost_treat else ''
	protoItem["opscost_treat"] = str(firstPageInfo.opscost_treat) if firstPageInfo.opscost_treat else ''
	protoItem["anesthesiacost_treat"] = str(
		firstPageInfo.anesthesiacost_treat) if firstPageInfo.anesthesiacost_treat else ''
	protoItem["surgicacost_trear"] = str(firstPageInfo.surgicacost_trear) if firstPageInfo.surgicacost_trear else ''
	protoItem["kfcost"] = str(firstPageInfo.kfcost) if firstPageInfo.kfcost else ''
	protoItem["cmtreatcost"] = str(firstPageInfo.cmtreatcost) if firstPageInfo.cmtreatcost else ''
	protoItem["wmmedicine"] = str(firstPageInfo.wmmedicine) if firstPageInfo.wmmedicine else ''
	protoItem["antibacterial"] = str(firstPageInfo.antibacterial) if firstPageInfo.antibacterial else ''
	protoItem["medicine_cpm"] = str(firstPageInfo.medicine_cpm) if firstPageInfo.medicine_cpm else ''
	protoItem["medicine_chm"] = str(firstPageInfo.medicine_chm) if firstPageInfo.medicine_chm else ''
	protoItem["bloodcost"] = str(firstPageInfo.bloodcost) if firstPageInfo.bloodcost else ''
	protoItem["productcost_bdb"] = str(firstPageInfo.productcost_bdb) if firstPageInfo.productcost_bdb else ''
	protoItem["productcost_qdb"] = str(firstPageInfo.productcost_qdb) if firstPageInfo.productcost_qdb else ''
	protoItem["productcost_nxyz"] = str(firstPageInfo.productcost_nxyz) if firstPageInfo.productcost_nxyz else ''
	protoItem["productcost_xbyz"] = str(firstPageInfo.productcost_xbyz) if firstPageInfo.productcost_xbyz else ''
	protoItem["consumables_exam"] = str(firstPageInfo.consumables_exam) if firstPageInfo.consumables_exam else ''
	protoItem["consumables_treat"] = str(firstPageInfo.consumables_treat) if firstPageInfo.consumables_treat else ''
	protoItem["consumables_ops"] = str(firstPageInfo.consumables_ops) if firstPageInfo.consumables_ops else ''
	protoItem["othercost"] = str(firstPageInfo.othercost) if firstPageInfo.othercost else ''
	protoItem["ext_contents"] = firstPageInfo.ext_contents or ''
	protoItem["poison_diag"] = firstPageInfo.poison_diag or ''
	protoItem["poison_code"] = firstPageInfo.poison_code or ''


def unmarshalCaseEmr(emr, htmlDict, protoItem, contentsDict=None):
	if not emr:
		return
	IMAGE_PAT = re.compile(r'"data:image/png;base64,.*?"')
	protoItem["id"] = emr.id or 0
	protoItem["docId"] = emr.docId or ""
	protoItem["caseId"] = emr.caseId or ""
	protoItem["documentName"] = emr.documentName or ""
	protoItem["department"] = emr.department or ""
	protoItem["author"] = emr.author or ""
	protoItem["createTime"] = emr.createTime.strftime('%Y-%m-%d %H:%M:%S') if emr.createTime else ""
	protoItem["updateTime"] = emr.updateTime.strftime('%Y-%m-%d %H:%M:%S') if emr.updateTime else ""
	if len(protoItem["updateTime"]) < 19 and len(protoItem["updateTime"]) > 0:
		protoItem["updateTime"] = "000" + protoItem["updateTime"]
	protoItem["recordTime"] = emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
	protoItem["isSave"] = emr.isSave or False
	protoItem["isCheck"] = emr.checkFlag or False
	protoItem["htmlContent"] = IMAGE_PAT.sub(re_image, htmlDict.get(emr.emrContentId, "") or "")
	protoItem["contents"] = IMAGE_PAT.sub(re_image, str(contentsDict.get(emr.emrContentId, {}))) if contentsDict else ""
	protoItem["refuseDoctor"] = emr.refuseCode or ""
	protoItem["firstSaveTime"] = emr.first_save_time.strftime('%Y-%m-%d %H:%M:%S') if emr.first_save_time else ""
	# if hasattr(protoItem, "docTypes"):
	for doc_type in emr.getDocTypes():
		protoItem["docTypes"].append(doc_type)


def unmarshalMedicalAdvice(order, protoItem):
	if not order:
		return
	protoItem["order_no"] = order.order_no or ""
	protoItem["order_type"] = order.order_type or ""
	protoItem["set_no"] = order.set_no or ""
	protoItem["order_seq"] = order.order_seq or ""
	protoItem["date_start"] = order.date_start.strftime('%Y-%m-%d %H:%M') if order.date_start else ""
	protoItem["date_stop"] = order.date_stop.strftime('%Y-%m-%d %H:%M') if order.date_stop else ""
	protoItem["code"] = order.code or ""
	protoItem["name"] = order.std_name or ""
	protoItem["model"] = order.model.model or ""
	protoItem["dosage"] = order.dosage or ""
	protoItem["unit"] = order.unit or ""
	protoItem["instruct_code"] = order.instruct_code or ""
	protoItem["instruct_name"] = order.instruct_name or ""
	protoItem["frequency_code"] = order.frequency_code or ""
	# protoItem["frequency_name"] = order.frequency_name or ""
	protoItem["at_time"] = order.at_time or ""
	protoItem["doctor_code"] = order.doctor_code or ""
	protoItem["doctor"] = order.doctor or ""
	protoItem["stop_doctor_code"] = order.stop_doctor_code or ""
	protoItem["stop_doctor"] = order.stop_doctor or ""
	protoItem["do_date"] = order.do_date or ""
	protoItem["nurse"] = order.nurse or ""
	protoItem["dept_code"] = order.dept_code or ""
	protoItem["dept_name"] = order.dept_name or ""
	protoItem["status"] = order.status or ""
	protoItem["order_flag"] = order.order_flag or ""
	protoItem["order_flag_name"] = order.order_flag_name or ""
	protoItem["self_flag"] = order.self_flag or ""
	# protoItem["print_flag"] = order.print_flag or ""
	protoItem["remark"] = order.remark or ""
	protoItem["total_dosage"] = order.total_dosage or ""
	protoItem["npl"] = order.npl or ""
	# protoItem["dosage_day"] = order.dosage_day or ""
	protoItem["orderStatus"] = str(order.exec_flag) if order.exec_flag else ""
	protoItem["std_code"] = order.std_code or ""
	protoItem["std_name"] = order.name or ""


def unmarshalLabReport(report, protoItem):
	if not report:
		return
	# 化验报告单基本信息
	protoItem["id"] = report.getReportId()
	protoItem["testname"] = report.testname or ''
	protoItem["specimen"] = report.specimen or ''
	protoItem["requestTime"] = report.requestTime.strftime('%Y-%m-%d %H:%M:%S') if report.requestTime else ''
	protoItem["reportTime"] = report.reportTime.strftime('%Y-%m-%d %H:%M:%S') if report.reportTime else ''
	protoItem["requestDepartment"] = report.requestDepartment or ''
	protoItem["requestDoctor"] = report.requestDoctor or ''
	if report.contents:
		# 化验项目结果
		for content in report.contents:
			subItem = {}  # protoItem.items.add()
			subItem["id"] = content.id
			subItem["itemname"] = content.std_name or content.itemname or ''
			subItem["code"] = content.code or ''
			subItem["result"] = content.result or ''
			subItem["unit"] = content.unit or ''
			flag = content.resultFlag
			stand_flag = lab_result_flag_dict.get(flag, None)
			subItem["resultFlag"] = stand_flag or flag or ''
			subItem["valrange"] = content.valrange or ''
			subItem["abnormalFlag"] = str(content.abnormalFlag) if content.abnormalFlag else ''
			subItem["abnormalIcon"] = LAB_ABNORMAL_ICON.get(content.resultFlag) or ''
			subItem["std_code"] = content.std_code or ''
			subItem["std_name"] = content.itemname or ''
			protoItem["items"].append(subItem)


def unmarshalExamReport(exam, protoItem):
	if not exam:
		return
	# 化验报告单基本信息
	protoItem["id"] = exam.getReportId()
	protoItem["examname"] = exam.examname or ''
	protoItem["examtype"] = exam.examtype or ''
	protoItem["position"] = exam.position or ''
	protoItem["requestTime"] = exam.requestTime.strftime('%Y-%m-%d %H:%M:%S') if exam.requestTime else ''
	protoItem["reportTime"] = exam.reportTime.strftime('%Y-%m-%d %H:%M:%S') if exam.reportTime else ''
	protoItem["requestDepartment"] = exam.requestDepartment or ''
	protoItem["requestDoctor"] = exam.requestDoctor or ''
	protoItem["reviewDoctor"] = exam.reviewDoctor or ''
	protoItem["execDepartment"] = exam.execDepartment or ''
	protoItem["execDoctor"] = exam.execDoctor or ''
	if exam.contents:
		# 化验项目结果
		for content in exam.contents:
			subItem = {}  # protoItem.items.add()
			subItem["id"] = content.id
			subItem["itemname"] = content.itemname or ''
			subItem["description"] = content.description or ''
			subItem["result"] = content.result or ''
			protoItem["items"].append(subItem)


def unmarshalTemperatureInfo(protoItem, temperatureInfo):
	protoItem["id"] = temperatureInfo.id or ''
	protoItem["item_name"] = temperatureInfo.item_name or ''
	protoItem["value"] = temperatureInfo.value or ''
	protoItem["unit"] = temperatureInfo.unit or ''
	protoItem["time"] = temperatureInfo.time.strftime('%Y-%m-%d %H:%M:%S') if temperatureInfo.time else ''


def unmarshalDiagnosisInfo(protoItem, diagnosisInfo):
	protoItem["id"] = str(diagnosisInfo.id) or ''
	protoItem["diagId"] = diagnosisInfo.diagId or ''
	protoItem["code"] = diagnosisInfo.code or ''
	protoItem["name"] = diagnosisInfo.name or ''
	protoItem["type"] = diagnosisInfo.type or ''
	protoItem["mainFlag"] = str(diagnosisInfo.mainFlag) if diagnosisInfo.mainFlag else ''
	protoItem["diagtime"] = diagnosisInfo.diagtime.strftime('%Y-%m-%d %H:%M:%S') if diagnosisInfo.diagtime else ''


def unmarshalfpdiagnosis(fpdiagnosis, protoItem):
	if not fpdiagnosis:
		return
	protoItem["icdcode"] = fpdiagnosis.icdcode or ''
	protoItem["icdname"] = fpdiagnosis.std_name or ''
	protoItem["typecode"] = fpdiagnosis.typecode or ''
	protoItem["typename"] = fpdiagnosis.typename or ''
	protoItem["incondition"] = fpdiagnosis.incondition or ''
	protoItem["prognosis"] = fpdiagnosis.prognosis or ''
	protoItem["diagtime"] = fpdiagnosis.diagtime.strftime('%Y-%m-%d %H:%M:%S') if fpdiagnosis.diagtime else ''
	protoItem["datemodified"] = fpdiagnosis.datemodified.strftime('%Y-%m-%d %H:%M:%S') if fpdiagnosis.datemodified else ''
	protoItem["diagnumber"] = fpdiagnosis.diagnumber or ''
	protoItem["diagdoctor"] = fpdiagnosis.diagdoctor or ''
	protoItem["std_code"] = fpdiagnosis.std_code or ''
	protoItem["std_name"] = fpdiagnosis.icdname or ''


def unmarshalfpoperation(fpoperation, protoItem):
	if not fpoperation:
		return
	protoItem["oper_class"] = fpoperation.oper_class or ''
	protoItem["oper_no"] = fpoperation.oper_no or ''
	protoItem["oper_code"] = fpoperation.oper_code or ''
	protoItem["oper_name"] = fpoperation.std_name or ''
	protoItem["oper_level"] = fpoperation.oper_level or ''
	protoItem["oper_doctor"] = fpoperation.oper_doctor or ''
	protoItem["assistant_1"] = fpoperation.assistant_1 or ''
	protoItem["assistant_2"] = fpoperation.assistant_2 or ''
	protoItem["cut_level"] = fpoperation.cut_level or ''
	protoItem["ans_doctor"] = fpoperation.ans_doctor or ''
	protoItem["oper_date"] = fpoperation.oper_date or ''
	protoItem["ane_method"] = fpoperation.ane_method or ''
	protoItem["heal_level"] = fpoperation.heal_level or ''
	protoItem["datemodified"] = fpoperation.datemodified.strftime('%Y-%m-%d %H:%M:%S') if fpoperation.datemodified else ''
	protoItem["std_code"] = fpoperation.std_code or ''
	protoItem["std_name"] = fpoperation.oper_name or ''


def unmarshalpathology(pathology, protoItem):
	protoItem["table"] = pathology.table or ''
	protoItem["key"] = pathology.key or ''
	protoItem["data"] = pathology.data or ''
	protoItem["create_at"] = pathology.create_at.strftime('%Y-%m-%d %H:%M:%S') if pathology.create_at else ''


def unmarshalQcAuditData(response, **kwargs):
	data_dict = dict()
	for key, values in kwargs.items():
		# data_dict[key] = list()
		for item in values:
			# emr
			if key == "unmarshal1":
				protoItem = {"docTypes": []}  # response.emr.add()
				htmlContent = {}
				xmlContents = {}
				if item.emrContentId:
					htmlContent[item.getEmrContentId()] = item.getEmrHtml() if item.documentName != '病案首页' else ''
					xmlContents[item.getEmrContentId()] = item.getEmrContents() if item.documentName != '病案首页' else ''
				unmarshalCaseEmr(item, htmlContent, protoItem, xmlContents)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["emr"].append(protoItem)
			# 医嘱
			if key == "unmarshal2":
				protoItem = {}  # response.doctor_advice.add()
				unmarshalMedicalAdvice(item, protoItem)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["doctor_advice"].append(protoItem)
			# 化验
			if key == "unmarshal3":
				protoItem = {"items": []}  # response.labs.add()
				unmarshalLabReport(item, protoItem)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["labs"].append(protoItem)
			if key == "unmarshal4":
				protoItem = {"items": []}  # response.exams.add()
				unmarshalExamReport(item, protoItem)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["exams"].append(protoItem)
			if key == "unmarshal5":
				protoItem = {}  # response.temperatureInfo.add()
				unmarshalTemperatureInfo(protoItem, item)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["temperatureInfo"].append(protoItem)
			if key == "unmarshal6":
				protoItem = {}  # response.diagnosisInfo.add()
				unmarshalDiagnosisInfo(protoItem, item)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["diagnosisInfo"].append(protoItem)
			if key == "unmarshal7":
				protoItem = {}  # response.fpDiagnosisInfo.add()
				unmarshalfpdiagnosis(item, protoItem)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["fpDiagnosisInfo"].append(protoItem)
			if key == "unmarshal8":
				protoItem = {}  # response.fpOperationInfo.add()
				unmarshalfpoperation(item, protoItem)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["fpOperationInfo"].append(protoItem)
			if key == "unmarshal9":
				protoItem = {}  # response.pathologyInfo.add()
				unmarshalpathology(item, protoItem)
				# data_dict[key].append(MessageToDict(protoItem, preserving_proto_field_name=True))
				response["pathologyInfo"].append(protoItem)
	return data_dict
