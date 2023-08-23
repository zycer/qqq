#!/usr/bin/env python3

from qcaudit.application.caseapplication import CaseApplication as _CaseApplication
from qcaudit.common.const import CASE_STATUS_ARCHIVED, AUDIT_TYPE_HOSPITAL, AUDIT_TYPE_FIRSTPAGE
# from qcaudit.common.exception import GrpcInvalidArgumentException
from qcaudit.config import Config
from qcaudit.common.result import CommonResult
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.service.protomarshaler import parseRating


class CaseApplication(_CaseApplication):
    @classmethod
    def writeArchiveScoreExcel(cls, sheet, caseList, patient_id_name="病历号"):
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