#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: statsrepository.py
@time: 2022/8/10 14:44
@desc:
"""
import copy
import logging
import random
from datetime import datetime, timedelta

import arrow
import xlsxwriter

from qcaudit.domain.stats.case_rate import CaseRate
from qcaudit.service.protomarshaler import parseStatusName
from qcaudit.utils.towebconfig import BRANCH_TARGET_SQL_FIELD_DICT


class StatsRepository:
    logger = logging.getLogger(__name__)

    @classmethod
    def format_defect_rate_data(cls, data, request, is_need_group=1):
        """
        格式化缺陷率统计数据
        :return:
        """
        request_type = request.type
        apply_index = 3 if request_type == "科室" else 2
        defect_index = 4 if request_type == "科室" else 3
        attend_index = 2 if request_type == "科室" else 1
        res = {}
        total_apply = 0
        total_defect = 0
        for item in data:
            if len(item) == 1:
                return []
            if not res.get(item[0]):
                res[item[0]] = {"apply_total": 0, "defect_total": 0, "data": [], "g_data": {}}
            res[item[0]]["apply_total"] += int(item[apply_index] or 0)
            res[item[0]]["defect_total"] += int(item[defect_index] or 0)
            total_apply += int(item[apply_index] or 0)
            total_defect += int(item[defect_index] or 0)
            tmp = {"attend": item[attend_index], "apply_num": int(item[apply_index] or 0),
                   "defect_num": int(item[defect_index] or 0), "deptHide": item[0]}
            res[item[0]]["data"].append(tmp)
            if request_type == "科室":
                tmp["groupHide"] = item[1]
                if not res[item[0]]["g_data"].get(item[1]):
                    res[item[0]]["g_data"][item[1]] = {"apply_total": 0, "defect_total": 0, "data": []}
                res[item[0]]["g_data"][item[1]]["apply_total"] += int(item[apply_index] or 0)
                res[item[0]]["g_data"][item[1]]["defect_total"] += int(item[defect_index] or 0)
                res[item[0]]["g_data"][item[1]]["data"].append(tmp)
        if not res:
            return []
        res1 = [{"dept": "总计", "apply_num": total_apply, "defect_num": total_defect, "deptHide": request.department, "groupHide": request.group, "attendHide": request.attend}]
        for dept, dept_data in res.items():
            res1.append({"dept": dept, "group": "", "apply_num": dept_data["apply_total"], "defect_num": dept_data["defect_total"], "deptHide": dept, "attendHide": request.attend, "groupHide": request.group})
            if request_type == "科室" and is_need_group == 1:
                for group, g_data in dept_data["g_data"].items():
                    res1.append({"dept": "", "group": group, "attend": "", "apply_num": g_data["apply_total"],
                                 "defect_num": g_data["defect_total"], "deptHide": dept, "groupHide": group, "attendHide": request.attend})
                    for item in g_data["data"]:
                        tmp = {"dept": "", "group": item.get("group", ""), "attend": item["attend"],
                               "apply_num": int(item["apply_num"]), "defect_num": int(item["defect_num"]), "deptHide": dept, "groupHide": group, "attendHide": item["attend"]}
                        res1.append(tmp)
            else:
                for item in dept_data["data"]:
                    tmp = {"dept": "", "group": item.get("group", ""), "attend": item["attend"], "groupHide": item.get("group", ""),
                           "apply_num": int(item["apply_num"]), "defect_num": int(item["defect_num"]), "deptHide": dept, "attendHide": item["attend"]}
                    res1.append(tmp)
        return res1

    @classmethod
    def get_year_start_time(cls, endTime):
        """
        获取一年范围时间的起始时间
        :param endTime:
        :return:
        """
        endTime = datetime.strptime(endTime, "%Y-%m-%d")
        return endTime - timedelta(days=365)

    @classmethod
    def GetBranchTimelinessRateData(cls, session, request, target_field, is_export=0):
        """
        查询指标明细数据
        :return:
        """
        start = request.start or 0
        size = request.size or 10
        if request.targetName in ("临床用血相关记录符合率", "植入物相关记录符合率", "入院记录24小时内完成率", "手术记录24小时内完成率", "出院记录24小时内完成率", "病案首页24小时内完成率"):
            query_sql = '''select distinct IF(c.inpNo is not null, c.inpNo, c.patientId) patientId, c.name, ifnull(dds.statis_name,ce.outdeptname), c.wardName, c.admitTime, ce.dischargetime, ce.attendDoctor, ce.auditflag, %s, c.InpNo from case_medical_temp cmt inner join `case` c on cmt.caseId = c.caseId inner join case_extend ce on cmt.caseId = ce.caseid left join dim_dept_statis dds on ce.outdeptid = dds.deptid where ce.status<>5 ''' % BRANCH_TARGET_SQL_FIELD_DICT.get(request.targetName)
            query_count_sql = '''select count(*) from case_medical_temp cmt inner join `case` c on cmt.caseId = c.caseId inner join case_extend ce on cmt.caseId = ce.caseid left join dim_dept_statis dds on ce.outdeptid = dds.deptid where ce.status<>5 '''
        else:
            query_sql = '''select distinct IF(c.inpNo is not null, c.inpNo, c.patientId) patientId, c.name, ifnull(dds.statis_name,ce.outdeptname), c.wardName, c.admitTime, ce.dischargetime, ce.attendDoctor, ce.auditflag, %s, c.InpNo from case_extend ce inner join `case` c on ce.caseid = c.caseId left join dim_dept_statis dds on ce.outdeptid = dds.deptid where ce.status<>5 ''' % BRANCH_TARGET_SQL_FIELD_DICT.get(request.targetName)
            query_count_sql = '''select count(*) from case_extend ce inner join `case` c on ce.caseid = c.caseId left join dim_dept_statis dds on ce.outdeptid = dds.deptid where ce.status<>5 '''
        condition = ""
        if request.branch and request.branch != "全院":
            condition += '''and c.branch = "%s" ''' % request.branch
        if request.department and request.department != "总计":
            condition += '''and ifnull(dds.statis_name, ce.outdeptname) = "%s" ''' % request.department
        if request.attend and request.attend != "总计":
            condition += '''and ce.attendDoctor = "%s" ''' % request.attend
        if request.startTime:
            condition += '''and ce.dischargetime >= "%s" ''' % request.startTime
        if request.endTime:
            condition += '''and ce.dischargetime <= "%s 23:59:59" ''' % request.endTime
        if request.ward and request.ward != "总计":
            condition += '''and c.wardName = "%s" ''' % request.ward
        res_dict = {1: "是", 2: "否"}
        if res_dict.get(request.accordFlag):
            if request.targetName != "出院患者病历2日归档率":
                condition += '''and %s ''' % (target_field.format(res=res_dict[request.accordFlag]))
            else:
                compare_dict = {1: "<=", 2: ">"}
                condition += '''and %s ''' % (target_field.format(compare=compare_dict[request.accordFlag]))
        time_dict = {"按时完成": "按时完成", "超时完成": "超时完成", "未完成": "未完成"}
        if time_dict.get(request.timeFlag) and request.targetName in ("入院记录24小时内完成率", "手术记录24小时内完成率", "出院记录24小时内完成率", "病案首页24小时内完成率"):
            condition += {
                "入院记录24小时内完成率": "and cmt.inrecord24hcomplete_time = '{time}' ",
                "手术记录24小时内完成率": "and cmt.opsrecord24hcomplete_time = '{time}' ",
                "出院记录24小时内完成率": "and cmt.outrecord24hcomplete_time = '{time}' ",
                "病案首页24小时内完成率": "and cmt.firstpage24hcomplete_time = '{time}' ",
            }.get(request.targetName).format(time=time_dict[request.timeFlag])

        limit_sql = '''limit %s, %s ''' % (start, size)

        query_sql += condition
        if not is_export:
            query_sql += limit_sql
        query = session.execute(query_sql)
        queryset = query.fetchall()
        query_count_sql += condition
        query_count = session.execute(query_count_sql)
        total = query_count.fetchone()[0]
        row_data = []
        title_list = ["病历号", "姓名", "科室", "病区", "入院日期", "出院日期", "责任医生", "病历状态", "指标符合状态"]
        if request.targetName in ("入院记录24小时内完成率", "手术记录24小时内完成率", "出院记录24小时内完成率", "病案首页24小时内完成率"):
            title_list.append("指标完成时效")
        tmp_data = []
        for item in queryset:
            tmp = {}
            tmp_data.append(item[8])
            for index in range(len(title_list)):
                value = str(item[index] or "")
                if index == 4:
                    value = item[index].strftime("%Y-%m-%d") if item[index] else ""
                if index == 8:
                    value = "符合" if item[index] == "是" else "不符合"
                    if request.targetName == "出院患者病历2日归档率":
                        value = "符合" if (item[index] or 0) <= 2 else "不符合"
                tmp[title_list[index]] = value
            row_data.append(tmp)
        return row_data, total

    @classmethod
    def get_end_time(cls, endTime):
        """
        获取当月最后一天
        :param endTime:
        :return:
        """
        endTime = datetime.strptime(endTime, "%Y-%m-%d")
        next_month = endTime.replace(day=28) + timedelta(days=4)
        res_time = next_month - timedelta(days=next_month.day)
        return res_time.strftime("%Y-%m-%d")

    @classmethod
    def get_start_time(cls, endTime):
        """
        获取截止日期前6个月起始时间
        :param endTime:
        :return:
        """
        t = int(endTime[5:7])
        y = endTime[:4]
        if t >= 6:
            m = t - 5
        else:
            m = 12 - (5 - t)
            y = str(int(y) - 1)
        m = str(m) if m > 9 else "0" + str(m)
        return y + "-" + m + "-01"

    @classmethod
    def get_call_disease_contrast_qc_sql(cls, request=None, t="折线"):
        begin_date = arrow.get(request.startTime).naive.strftime('%Y-%m-%d') if request.startTime else ''
        end_date = arrow.get(request.endTime).naive.strftime('%Y-%m-%d') if request.endTime else ''
        _type = request.contrast.type
        department = request.department
        disease = request.disease
        status = request.status
        target_name = ""
        if _type == "year":
            target_name = "质控指标雷达图对比" if "雷达" in t else "质控指标折线图对比"
        if _type == "department":
            target_name = "科室质控雷达图对比" if "雷达" in t else "科室质控折线图对比"
        if _type == "doctor":
            target_name = "医生质控雷达图对比" if "雷达" in t else "医生质控折线图对比"
        call_proc_sql = f"""call pr_disease_qc_index ('{target_name}','{begin_date}','{end_date}','{department}','','{disease}','','{status}','')"""
        return call_proc_sql

    @classmethod
    def get_call_disease_sql(cls, target_name, request=None, only_dict=False):
        if only_dict:
            call_proc_sql = f"""call pr_disease_index ('{target_name}','','','','','')"""
            return call_proc_sql
        begin_date = arrow.get(request.startTime).naive.strftime('%Y-%m-%d') if request.startTime else ''
        end_date = arrow.get(request.endTime).naive.strftime('%Y-%m-%d') if request.endTime else ''
        dept, disease_name, disease_type = '', '', ''
        if getattr(request, 'department') is not None:
            dept = request.department or '全部科室'
        if getattr(request, 'disease') is not None:
            disease_name = request.disease or '全部病种'
        if getattr(request, 'diseaseType') is not None:
            disease_type = request.diseaseType or '全部类型'
        call_proc_sql = f"""call pr_disease_index ('{target_name}','{begin_date}','{end_date}','{dept}',
                    '{disease_name}','{disease_type}')"""
        return call_proc_sql

    @classmethod
    def get_disease_audit_contrast_common_header_data(cls, cursor, request, t="折线"):
        contrast_values = copy.copy(list(request.contrast.value))
        if "雷达" in t:
            result = {i: {j: 0 for j in request.indicators} for i in contrast_values}
            radar_max = {j: 0 for j in request.indicators}
            indicator_unit_dict = dict()
            indicator_unit_sql = """select d.name, d.unit from dim_ind d """
            query_set = cursor.execute(indicator_unit_sql)
            indicator_unit = query_set.fetchall()
            for item in indicator_unit:
                indicator_unit_dict[item[0]] = item[1]
            if request.contrast.type != 'year':
                queryset, col_dict = cls.get_data(cursor, request, t)
                for col in request.indicators:
                    index = col_dict.get(col, None)
                    if index is not None:
                        for item in queryset:
                            contrast = item[0]
                            if contrast not in contrast_values:
                                continue
                            if contrast:
                                result[contrast][col] = cls.keep_one(item[index])
                                if item[index] > radar_max[col]:
                                    radar_max[col] = item[index]
                return result, radar_max, indicator_unit_dict
            else:
                start = '-01-01'
                end = '-12-31'
                for year in contrast_values:
                    request.startTime = year + start
                    request.endTime = year + end
                    queryset, col_dict = cls.get_data(cursor, request, t)
                    for col in request.indicators:
                        index = col_dict.get(col, None)
                        if index is not None:
                            for item in queryset:
                                result[year][col] = cls.keep_one(item[index])
                                if item[index] > radar_max[col]:
                                    radar_max[col] = item[index]
                return result, radar_max, indicator_unit_dict
        else:
            result = {i: {j: {} for j in request.contrast.value} for i in request.indicators}
            if request.contrast.type != 'year':
                queryset, col_dict = cls.get_data(cursor, request, t)
                for col in request.indicators:
                    index = col_dict.get(col, None)
                    if index is not None:
                        for item in queryset:
                            contrast = item[1]
                            if contrast not in contrast_values:
                                continue
                            if contrast:
                                result[col][item[1]][item[0]] = cls.keep_one(item[index])
                return result
            else:
                start = '-01-01'
                end = '-12-31'
                for year in contrast_values:
                    request.startTime = year + start
                    request.endTime = year + end
                    queryset, col_dict = cls.get_data(cursor, request, t)
                    for col in request.indicators:
                        index = col_dict.get(col, None)
                        if index is not None:
                            for item in queryset:
                                data_list = item[0].split('-')
                                contrast = data_list[0]
                                month = data_list[1]
                                if contrast not in contrast_values:
                                    continue
                                if contrast:
                                    result[col][contrast][month] = cls.keep_one(item[index]) if item[index] else '0'
                return result

    @classmethod
    def get_data(cls, cursor, request, t):
        call_proc_sql = StatsRepository.get_call_disease_contrast_qc_sql(request, t)
        query = cursor.execute(call_proc_sql)
        columns = query.keys()
        col_dict = {columns[i]: i for i in range(len(columns))}
        cls.logger.info("get_common_stats_disease_contrast_qc_response, call_proc_sql: %s", call_proc_sql)
        queryset = query.fetchall()
        return queryset, col_dict

    @classmethod
    def keep_one(cls, num, ratio=False):
        """
        保留一位小数
        :param num:
        :param ratio: 是否带单位符号
        :return:
        """
        if not num:
            num = 0
        minus = False
        if num < 0:
            num = float(str(num)[1:])
            minus = True
        symbol = '%'
        if num >= 1:
            x = '%.1f' % num
        elif num >= 0.1:
            x = '%0.2f' % num  # 0.xx
        elif num >= 0.01:
            if ratio:
                n = num * 10
                x, symbol = '%0.2f' % n, '‰'  # 0.xx
            else:
                x = '%.1f' % num
        elif num > 0.0001:
            if ratio:
                n = num * 100
                x, symbol = '%0.2f' % n, '‱'
            else:
                x = '%.1f' % num
        else:
            x = '0'
        if num == 100:
            x = "100"
        if minus and x != '0':
            x = "-" + x
        if ratio:
            return x + symbol
        return x

    @classmethod
    def get_call_disease_qc_sql(cls, target_name, request=None, only_dict=False, front_year=0):
        if only_dict:
            call_proc_sql = f"""call pr_disease_qc_index ('{target_name}','','','','','')"""
            return call_proc_sql
        if front_year:
            begin_date = arrow.get(request.startTime).shift(years=-front_year).naive.strftime(
                '%Y-%m-%d') if request.startTime else ''
            end_date = arrow.get(request.endTime).shift(years=-front_year).naive.strftime(
                '%Y-%m-%d') if request.endTime else ''
        else:
            begin_date = arrow.get(request.startTime).naive.strftime('%Y-%m-%d') if request.startTime else ''
            end_date = arrow.get(request.endTime).naive.strftime('%Y-%m-%d') if request.endTime else ''
        department, disease, status, _type, target, doctor = '', '', '', '', '', ''
        if getattr(request, 'department', None) is not None:
            department = request.department or '全部科室'
        if getattr(request, 'disease', None) is not None:
            disease = request.disease or '全部病种'
        if getattr(request, 'status', None) is not None:
            status = request.status
        if getattr(request, 'type', None) is not None:
            _type = request.type
        if getattr(request, 'target', None) is not None:
            target = request.target or "覆盖病种数"
        if getattr(request, 'doctor', None) is not None:
            doctor = request.doctor or ""
        call_proc_sql = f"""call pr_disease_qc_index ('{target_name}','{begin_date}','{end_date}','{department}','{doctor}','{disease}','{_type}','{status}','{target}')"""
        return call_proc_sql

    @classmethod
    def get_init_dict(cls, startTime, endTime):
        """
        获取初始化带时间默认值字典
        :return:
        """

        def get_str_month(month):
            month = str(month)
            if len(month) == 1:
                month = "0" + month
            return month

        start_year = startTime[:4]
        end_year = endTime[:4]
        start_month = startTime[5:7]
        end_month = endTime[5:7]
        diff = int(end_year) - int(start_year)
        res = {}
        if not diff:
            for i in range(int(start_month), int(end_month) + 1):
                res[start_year + "-" + get_str_month(i)] = 0
        else:
            for i in range(int(start_month), 13):
                res[start_year + "-" + get_str_month(i)] = 0
            if diff > 1:
                for year in range(diff - 1):
                    new_year = str(int(start_year) + year + 1)
                    for i in range(1, 13):
                        res[new_year + "-" + get_str_month(i)] = 0
            for i in range(1, int(end_month) + 1):
                res[end_year + "-" + get_str_month(i)] = 0
        return res

    @classmethod
    def verify_stats_level(cls, qc_stats_level):
        """
        校验统计级别是甲级等还是优秀等
        :return:
        """
        if "甲级" in qc_stats_level:
            return 1

    @classmethod
    def verify_row_data(cls, data):
        """
        校验是否为基础数据
        :param data:
        :return:
        """
        for key, value in data.items():
            if value != "":
                return 1

    @classmethod
    def write_defect_rate_excel(cls, title, data, file_name):
        """
        缺陷率统计写excel
        :return:
        """
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet()
        for i in range(len(title)):
            worksheet.write(0, i, title[i])

        row = 1
        for item in data:
            apply_num = item.get("apply_num") or 0
            defect_num = item.get("defect_num") or 0
            rate = cls.keep_one(defect_num / apply_num * 100, True) if apply_num else "0%"
            row_data = [item.get("dept") or "", item.get("attend") or "", str(apply_num), str(defect_num), rate]
            if len(title) == 6:
                row_data.insert(1, item.get("group") or "")
            for col in range(len(row_data)):
                worksheet.write(row, col, row_data[col])
            row += 1

        for col in range(len(title)):
            worksheet.set_column(0, col, 22)
        workbook.close()

    @classmethod
    def get_defect_rate_detail_data(cls, session, case_model, request, is_export=0):
        """
        查询缺陷统计率明细
        :return:
        """
        query = session.query(CaseRate, case_model).join(case_model, CaseRate.caseid == case_model.caseId)
        if request.department:
            query = query.filter(CaseRate.outdeptname.in_(request.department.split(",")))
        if request.group:
            query = query.filter(CaseRate.medicalgroupname.in_(request.group.split(",")))
        if request.ward:
            query = query.filter(CaseRate.outhosward.in_(request.ward.split(",")))
        if request.attend:
            query = query.filter(CaseRate.attendDoctor.in_(request.attend.split(",")))
        if request.startScore:
            query = query.filter(CaseRate.score >= float(request.startScore))
        if request.endScore:
            query = query.filter(CaseRate.score <= float(request.endScore))
        if request.branch and request.branch not in ("全部", "全部院区"):
            query = query.filter(CaseRate.branch == request.branch)
        standard_dict = {1: "是", 2: "否"}
        if standard_dict.get(request.qualifiedFlag):
            query = query.filter(CaseRate.is_standard == standard_dict[request.qualifiedFlag])
        if request.status:
            query = query.filter(CaseRate.status == request.status)
        if request.startTime:
            query = query.filter(CaseRate.dischargetime >= request.startTime)
        if request.endTime:
            query = query.filter(CaseRate.dischargetime <= request.endTime)
        total = query.count()
        if not is_export:
            start = request.start or 0
            size = request.size or 10
            query = query.slice(start, start + size)
        return total, query.all()

    @classmethod
    def write_defect_detail_excel(cls, title, data, file_name):
        """
        缺陷率明细写excel
        :return:
        """
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet()
        for i in range(len(title)):
            worksheet.write(0, i, title[i])

        row = 1
        for item, case in data:
            row_data = [case.inpNo or case.patientId or "", item.name or "", item.admittime.strftime("%Y-%m-%d") if item.admittime else "",
                        item.dischargetime.strftime("%Y-%m-%d") if item.dischargetime else "", ]
            if len(title) == 10:
                row_data += [item.outdeptname or "", item.medicalgroupname or ""]
            else:
                row_data += [item.outhosward or ""]
            row_data += [item.attendDoctor or "", str(item.score or 0), item.is_standard or "", parseStatusName(False, item.status)]
            for col in range(len(row_data)):
                worksheet.write(row, col, row_data[col])
            row += 1

        workbook.close()

    @classmethod
    def get_defect_rate_detail_export_title_name(cls, request):
        """
        缺陷统计-明细导出-文件名中括号内名称
        :param request:
        :return:
        """
        if not request.department and not request.group and not request.ward:
            return "总计"
        if request.attend and len(request.attend.split(",")) == 1:
            return request.attend
        if request.group and len(request.group.split(",")) == 1:
            return request.group
        if request.department and len(request.department.split(",")) == 1:
            return request.department
        if request.ward and len(request.ward.split(",")) == 1:
            return request.ward
        return "总计"

    @classmethod
    def get_running_case_info(cls, session, request, response):
        """
        质控分析-事中质控情况分析-病历数、累计减少问题数、平均病历减少问题数等
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        time_type, last_start_time, last_end_time = cls.get_chain_compare_rate_time(start_time, end_time)
        case_num_sql = """call pr_case_qc_analyse('病历数','','%s','','%s','%s','%s');""" % (branch, time_type, start_time, end_time)
        cls.logger.info("get_running_case_info, case_num_sql: %s", case_num_sql)
        query = session.execute(case_num_sql)
        case_num = query.fetchone()
        targets = ["病历数", "累计减少问题数", "平均每病历减少问题数"]
        for index in range(len(targets)):
            target = targets[index]
            target_info = {}  # response.targetInfo.add()
            target_info["name"] = target
            if len(case_num) == 6:
                target_info["count"] = str(case_num[index] or 0)
                target_info["sameCompareRate"] = str(case_num[index + 3] or 0)
            else:
                target_info["count"] = str(0)
                target_info["sameCompareRate"] = str(0)
            response["targetInfo"].append(target_info)

    @classmethod
    def get_chain_compare_rate_time(cls, startTime, endTime):
        """
        获取环比起始/截止时间
        :param startTime:
        :param endTime:
        :return:
        """
        if not startTime or not endTime:
            return "", ""
        start_month = int(startTime[5:7])
        new_start_month = start_month
        new_start_year = int(startTime[:4])

        end_month = int(endTime[5:7])
        new_end_month = end_month
        new_end_year = int(endTime[:4])

        if end_month - start_month == 0:
            # 月份
            time_type = "month"
            new_start_month = start_month - 1
            new_end_month = end_month - 1
            if new_start_month < 1:
                new_start_month = 12 + new_start_month
                new_start_year -= 1
            if new_end_month < 1:
                new_end_month = 12
                new_end_year -= 1

        elif end_month - start_month == 2:
            # 季度
            time_type = "quarter"
            new_start_month = start_month - 3
            new_end_month = end_month - 3
            if new_start_month < 1:
                new_start_month = 12 + new_start_month
                new_start_year -= 1
            if new_end_month < 1:
                new_end_month = 12
                new_end_year -= 1
        else:
            # 年
            time_type = "year"
            new_start_year -= 1
            new_end_year -= 1

        if len(str(new_start_month)) == 1:
            new_start_month = "0" + str(new_start_month)
        if len(str(new_end_month)) == 1:
            new_end_month = "0" + str(new_end_month)

        new_start = str(new_start_year) + "-" + str(new_start_month) + "-" + startTime[-2:]
        new_end_year_month = str(new_end_year) + "-" + str(new_end_month)
        new_end = new_end_year_month + "-" + str(cls.get_month_last_day(new_end_year_month))
        return time_type, new_start, new_end

    @classmethod
    def get_month_last_day(cls, day):
        """
        获取月份最后一天
        :param day:
        :return:
        """
        year = int(day[:4])
        if int(day[-2:]) in [4, 6, 9, 11]:
            return 30
        elif int(day[-2:]) == 2:
            return 29 if (not year % 4 and year % 100) or not year % 400 else 28
        return 31

    @classmethod
    def get_x_data(cls, startTime, endTime):
        """
        根据起始、截止时间 获取表横坐标数据
        :return:
        """
        start_month = int(startTime[5:7])
        end_month = int(endTime[5:7])

        today = datetime.now().strftime("%Y-%m-%d")
        all_month = [str(i) + "月" for i in range(1, 13)]

        if end_month - start_month == 0:
            # 月
            if today[:7] == startTime[:7]:
                range_day = min(int(today[-2:]) + 1, int(endTime[-2:]) + 1)
                return [str(i) + "号" for i in range(1, range_day)]
            return [str(i) + "号" for i in range(1, int(endTime[-2:]) + 1)]
        elif end_month - start_month == 2:
            # 季度
            if today[:4] == endTime[:4]:
                range_month = min(int(today[5:7]) + 1, int(end_month) + 1)
                return [str(i) + "月" for i in range(int(start_month), range_month)]
            return [str(i) + "月" for i in range(int(start_month), int(end_month) + 1)]
        else:
            # 年
            if today[:4] == endTime[:4]:
                return [str(i) + "月" for i in range(1, int(today[5:7]) + 1)]
            return all_month

    @classmethod
    def get_date_type(cls, startTime, endTime):
        """
        根据起始、截止时间获取时间范围类型
        :param startTime:
        :param endTime:
        :return:
        """
        start_month = int(startTime[5:7])
        end_month = int(endTime[5:7])

        if end_month - start_month == 0:
            # 月
            return "month"
        elif end_month - start_month == 2:
            # 季度
            return "quarter"
        else:
            # 年
            return "year"

    @classmethod
    def get_running_problem_info(cls, session, request, response):
        """
        累计问题趋势分析、平均每病历问题趋势分析
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        time_type, last_start_time, last_end_time = cls.get_chain_compare_rate_time(start_time, end_time)
        problem_sql = """call pr_case_qc_analyse('问题趋势分析','','%s','','%s','%s','%s');""" % (branch, time_type, start_time, end_time)
        cls.logger.info("get_running_problem_info, problem_sql: %s", problem_sql)
        query = session.execute(problem_sql)
        data = query.fetchall()

        first_names = ["累计问题趋势分析", "平均每病历问题趋势分析"]
        y_names = ["全部问题", "首次提交时问题"]
        x_data = cls.get_x_data(start_time, end_time)
        y_index = 0

        for first_name in first_names:
            for y_name in y_names:
                target_data = {"data": []}  # response.targetData.add()
                target_data["targetName"] = first_name
                target_data["yName"] = y_name
                y_index += 1
                if cls.exist_data(data, y_index):
                    for x_index in range(len(x_data)):
                        x_info = {}  # target_data.data.add()
                        x_info["xData"] = x_data[x_index]
                        x_info["yData"] = str(data[x_index][y_index] or 0)
                        target_data["data"].append(x_info)
                response["targetData"].append(target_data)

    @classmethod
    def exist_data(cls, data, y_index):
        """
        累计问题趋势分析、平均每病历问题趋势分析 是否有数据判断
        :return:
        """
        for item in data:
            if y_index < len(item) and item[y_index]:
                return True
        return False

    @classmethod
    def format_running_response(cls, data, target_name, y_names, response):
        """
        格式化写response
        :return:
        """
        for y_index in range(len(y_names)):
            y_name = y_names[y_index]
            target_data = {"data": []}  # response.targetData.add()
            target_data["targetName"] = target_name
            target_data["yName"] = y_name
            for item in data:
                if len(item) != 3:
                    continue
                x_info = {}  # target_data.data.add()
                x_info["xData"] = item[0] or ""
                x_info["yData"] = str(item[y_index + 1] or 0)
                target_data["data"].append(x_info)
            response["targetData"].append(target_data)

    @classmethod
    def get_running_dept_top(cls, session, request, response):
        """
        问题改善科室TOP10
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        dept_sql = """call pr_case_qc_analyse('问题改善科室top10','','%s','','','%s','%s');""" % (branch, start_time, end_time)
        cls.logger.info("get_running_dept_top, dept_sql: %s", dept_sql)
        query = session.execute(dept_sql)
        data = query.fetchall()

        target_name = "问题改善科室TOP10"
        y_names = ["累计减少问题数", "平均每病历减少问题数"]

        cls.format_running_response(data[:10], target_name, y_names, response)

    @classmethod
    def get_running_dept_info(cls, session, request, response, is_need_group):
        """
        对应科室问题改善诊疗组、医生TOP10情况
        :return:
        """
        department = request.department
        start_time = request.startTime
        end_time = request.endTime
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        target_name = "问题改善医疗组" if is_need_group == 1 else "问题改善医生TOP10"
        dept_sql = """call pr_case_qc_analyse('%s','%s','%s','','','%s','%s');""" % (target_name, department, branch, start_time, end_time)
        cls.logger.info("get_running_dept_info, dept_sql: %s", dept_sql)
        query = session.execute(dept_sql)
        data = query.fetchall() if is_need_group == 1 else query.fetchall()[:10]

        first_name = "【{}】{}".format(department, target_name)
        y_names = ["累计减少问题数", "平均每病历减少问题数"]

        cls.format_running_response(data, first_name, y_names, response)

    @classmethod
    def get_running_type(cls, session, request, response):
        """
        各类别问题改善情况分析
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        type_sql = """call pr_case_qc_analyse('各类别问题改善情况分析','','%s','','','%s','%s')""" % (branch, start_time, end_time)
        cls.logger.info("get_running_type, type_sql: %s", type_sql)
        query = session.execute(type_sql)
        data = query.fetchall()

        target_name = "各类别问题改善情况分析"
        y_names = ["全部问题", "首次提交时问题"]

        cls.format_running_response(data, target_name, y_names, response)

    @classmethod
    def get_running_type_info(cls, session, request, response):
        """
        对应类别问题改善情况分析
        :return:
        """
        problemType = request.problemType
        start_time = request.startTime
        end_time = request.endTime
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        sql = """call pr_case_qc_analyse('特定类别问题改善情况分析','','%s','%s','','%s','%s')""" % (branch, problemType, start_time, end_time)
        cls.logger.info("get_running_type_info, sql: %s", sql)
        query = session.execute(sql)
        data = query.fetchall()

        target_name = "【{}】问题改善情况分析".format(problemType)
        y_names = ["全部问题", "首次提交时问题"]

        cls.format_running_response(data, target_name, y_names, response)

    @classmethod
    def get_branch_timeliness_yaml(cls, yaml_str, fields):
        """
        根据不同配置 获取全院病案指标-病历书写时效性、诊疗行为符合率等 查询、导出配置文件
        :return:
        """
        field_list = fields.split(",")
        for z_name, en_name in BRANCH_TARGET_SQL_FIELD_DICT.items():
            if z_name in field_list:
                yaml_str = yaml_str.replace(en_name, "false")
            else:
                yaml_str = yaml_str.replace(en_name, "true")
        return yaml_str

    @classmethod
    def get_archive_sql_data(cls, target_name, session, request):
        """
        事后通用获取数据接口
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        date_type = cls.get_date_type(start_time, end_time)
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        department = request.department or ""
        problemType = request.problemType or ""
        sql = '''call pr_case_qc_analyse_after('%s','%s','%s','%s','%s','%s','%s');''' % (target_name, department, branch, problemType, date_type, start_time, end_time)
        cls.logger.info("get_archive_sql_data, sql: %s", sql)
        query = session.execute(sql)
        data = query.fetchall()
        return data

    @classmethod
    def get_zero_data(cls):
        """
        获取0数据
        :return:
        """
        return [0 for _ in range(10)]

    @classmethod
    def get_archive_case_num(cls, session, request, response):
        """
        质控分析-事后质控情况分析-病历数、病历缺陷率、平均每病案缺陷数
        :return:
        """
        target_name = '病历数'
        data = cls.get_archive_sql_data(target_name, session, request)
        data = data[0]
        if len(data) == 1:
            data = cls.get_zero_data()
        target_list = ["病历数", "病历缺陷率", "平均每病历缺陷数"]

        for i in range(len(target_list)):
            protoInfo = {}  # response.targetInfo.add()
            protoInfo["name"] = target_list[i]
            protoInfo["count"] = str(data[i] or 0)
            protoInfo["sameCompareRate"] = str(data[i + 3] or 0)
            if target_list[i] == "病历缺陷率":
                protoInfo["count"] = cls.keep_one(data[i])
                protoInfo["sameCompareRate"] = cls.keep_one(data[i + 3])
                protoInfo["countSuffix"] = "%"
                protoInfo["sameCompareRate"] += "%"
            response["targetInfo"].append(protoInfo)

    @classmethod
    def get_archive_ratio_info(cls, session, request, response):
        """
        质控分析-事后质控情况分析-病历质量趋势分析、病历问题数量趋势分析
        :return:
        """
        target_name = '问题趋势分析'
        data = cls.get_archive_sql_data(target_name, session, request)
        x_data = cls.get_x_data(request.startTime, request.endTime)

        y_info = {"病历质量趋势分析": ["病历缺陷率", "缺陷病历数"], "病历问题数量趋势分析": ["平均每病历问题数", "病历问题总数"]}
        cls.format_archive_x_response(response, data, y_info, x_data, keepOneFiled="病历缺陷率", suffixFields=["病历缺陷率"])

    @classmethod
    def format_archive_x_response(cls, response, data, y_info, x_data, keepOneFiled="-", suffixFields=[]):
        """
        通用事后带横坐标数据写入response
        :return:
        """
        y_index = 0

        for first_name, y_names in y_info.items():
            for y_name in y_names:
                protoData = {"data": []}  # response.targetData.add()
                protoData["targetName"] = first_name
                protoData["yName"] = y_name
                y_index += 1
                if cls.exist_data(data, y_index):
                    for x_index in range(len(x_data)):
                        protoDataData = {}  # protoData.data.add()
                        protoDataData["xData"] = x_data[x_index]
                        protoDataData["yData"] = str(data[x_index][y_index] or 0)
                        if y_name == keepOneFiled:
                            protoDataData["yData"] = cls.keep_one(data[x_index][y_index])
                        if y_name in suffixFields:
                            protoDataData["suffix"] = "%"
                        protoData["data"].append(protoDataData)
                response["targetData"].append(protoData)

    @classmethod
    def format_archive_response(cls, y_names, response, target_name, data, rate_y_name="", suffixFields=[]):
        """
        通用事后表格响应数据写入response
        :return:
        """
        y_index = 0
        for y_name in y_names:
            protoData = {"data": []}  # response.targetData.add()
            protoData["targetName"] = target_name
            protoData["yName"] = y_name
            y_index += 1
            if cls.exist_data(data, y_index):
                for item in data:
                    protoDataData = {}  # protoData.data.add()
                    protoDataData["xData"] = item[0] or ""
                    protoDataData["yData"] = str(item[y_index])
                    if y_name == rate_y_name:
                        protoDataData["yData"] = cls.keep_one(item[y_index])
                    if y_name in suffixFields:
                        protoDataData["suffix"] = "%"
                    protoData["data"].append(protoDataData)
            response["targetData"].append(protoData)

    @classmethod
    def get_archive_dept_top_info(cls, session, request, response):
        """
        质控分析-事后质控情况分析-病历质量重点关注科室top10
        :return:
        """
        target_name = '病历质量重点关注科室top10'
        data = cls.get_archive_sql_data(target_name, session, request)
        y_names = ["病历缺陷率", "缺陷病历数"]
        cls.format_archive_response(y_names, response, target_name, data[:10], rate_y_name="病历缺陷率", suffixFields=["病历缺陷率"])

    @classmethod
    def get_archive_doctor_top_info(cls, session, request, response, is_need_group):
        """
        质控分析-事后质控情况分析-对应科室-病历质量重点关注医生top10
        :return:
        """
        target_name = "病历质量重点关注医疗组" if is_need_group else "病历质量重点关注医生top10"
        first_name = "【%s】重点关注%s" % (request.department, "医疗组" if is_need_group else "医生TOP10")
        data = cls.get_archive_sql_data(target_name, session, request)
        if not is_need_group:
            data = data[:10]

        y_names = ["病历缺陷率", "缺陷病历数"]
        cls.format_archive_response(y_names, response, first_name, data, rate_y_name="病历缺陷率", suffixFields=["病历缺陷率"])

    @classmethod
    def get_archive_problem_num_top(cls, session, request, response):
        """
        质控分析-事后质控情况分析-病历问题数量重点关注科室top10
        :return:
        """
        target_name = "病历问题数量重点关注科室top10"
        data = cls.get_archive_sql_data(target_name, session, request)
        y_names = ["平均每病历问题数", "病历问题总数"]
        cls.format_archive_response(y_names, response, target_name, data[:10])

    @classmethod
    def get_archive_problem_num_doctor_top(cls, session, request, response, is_need_group):
        """
        质控分析-事后质控情况分析-对应科室-问题数量重点关注医生top10/诊疗组
        :return:
        """
        target_name = "病历问题数量重点关注医疗组" if is_need_group else "病历问题数量重点关注医生top10"
        first_name = "【%s】重点关注%s" % (request.department, "医疗组" if is_need_group else "医生TOP10")
        data = cls.get_archive_sql_data(target_name, session, request)
        if not is_need_group:
            data = data[:10]

        y_names = ["平均每病历问题数", "病历问题总数"]
        cls.format_archive_response(y_names, response, first_name, data)

    @classmethod
    def get_archive_problem_type(cls, session, request, response):
        """
        质控分析-事后质控情况分析-问题所属类别分析
        :return:
        """
        target_name = "问题所属类别分析"
        data = cls.get_archive_sql_data(target_name, session, request)

        for item in data:
            if not item[1] or item[1] <= 0:
                continue
            protoData = {"data": []}  # response.targetData.add()
            protoData["yName"] = item[0] or ""
            protoData["targetName"] = target_name
            protoDataData = {}  # protoData.data.add()
            protoDataData["xData"] = item[0] or ""
            protoDataData["yData"] = str(item[1])
            protoData["data"].append(protoDataData)
            response["targetData"].append(protoData)

    @classmethod
    def get_archive_problem_num_info(cls, session, request, response):
        """
        质控分析-事后质控情况分析-问题触发数量分析
        :return:
        """
        target_name = "特定问题触发数量分析"
        data = cls.get_archive_sql_data(target_name, session, request)
        first_name = "【%s】问题数量分析" % request.problemType

        y_names = ["问题数量"]
        cls.format_archive_response(y_names, response, first_name, data)

    @classmethod
    def get_veto_sql_data(cls, target_name, session, request):
        """
        强控通用获取数据接口
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        date_type = cls.get_date_type(start_time, end_time)
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        department = request.department or ""
        problemType = request.problemType or ""
        sql = '''call pr_case_qc_analyse_forced('%s','%s','%s','%s','%s','%s','%s');''' % (
            target_name, department, branch, problemType, date_type, start_time, end_time)
        cls.logger.info("get_veto_sql_data, sql: %s", sql)
        query = session.execute(sql)
        data = query.fetchall()
        return data

    @classmethod
    def get_veto_base_info(cls, session, request, response):
        """
        质控分析-强制拦截情况分析-病历拦截率、强制拦截数、累计减少问题数
        :return:
        """
        target_name = "病历数"
        data = cls.get_veto_sql_data(target_name, session, request)
        data = data[0]
        if len(data) == 1:
            data = cls.get_zero_data()
        target_list = ["病历强制拦截率", "强制拦截病历数", "累计减少强控问题数"]

        for i in range(len(target_list)):
            protoInfo = {}  # response.targetInfo.add()
            protoInfo["name"] = target_list[i]
            protoInfo["count"] = str(data[i] or 0)
            protoInfo["sameCompareRate"] = str(data[i + 3] or 0)
            if target_list[i] == "病历强制拦截率":
                protoInfo["count"] = cls.keep_one(data[i])
                protoInfo["sameCompareRate"] = cls.keep_one(data[i + 3])
                protoInfo["countSuffix"] = "%"
                protoInfo["sameCompareRate"] += "%"
            response["targetInfo"].append(protoInfo)

    @classmethod
    def get_veto_case_trend_info(cls, session, request, response):
        """
        质控分析-强制拦截情况分析-病历强制拦截率趋势分析、累计减少强制问题数趋势分析
        :return:
        """
        target_name = "病历强制拦截率趋势分析"
        data = cls.get_veto_sql_data(target_name, session, request)
        x_data = cls.get_x_data(request.startTime, request.endTime)
        y_info = {"病历强制拦截率趋势分析": ["病历强制拦截率", "强制拦截病历数"], "累计减少强制问题数趋势分析": ["累计减少强制问题数"]}
        cls.format_archive_x_response(response, data, y_info, x_data, keepOneFiled="病历强制拦截率", suffixFields=["病历强制拦截率"])

    @classmethod
    def get_veto_dept_top_info(cls, session, request, response):
        """
        质控分析-强制拦截情况分析-病历强制拦截率科室top10
        :return:
        """
        target_name = "病历强制拦截率科室top10"
        data = cls.get_veto_sql_data(target_name, session, request)
        y_names = ["病历强制拦截率", "强制拦截病历数"]
        cls.format_archive_response(y_names, response, target_name, data[:10], rate_y_name="病历强制拦截率", suffixFields=["病历强制拦截率"])

    @classmethod
    def get_veto_doctor_top_info(cls, session, request, response, is_need_group):
        """
        质控分析-强制拦截情况分析-对应科室医生top10
        :return:
        """
        target_name = "病历强制拦截率重点关注医疗组" if is_need_group == 1 else "病历强制拦截率重点关注医生top10"
        first_name = "【%s】重点关注%s" % (request.department, "医疗组" if is_need_group else "医生TOP10")
        data = cls.get_veto_sql_data(target_name, session, request)
        if is_need_group != 1:
            data = data[:10]

        y_names = ["病历强制拦截率", "强制拦截病历数"]
        cls.format_archive_response(y_names, response, first_name, data, rate_y_name="病历强制拦截率", suffixFields=["病历强制拦截率"])

    @classmethod
    def get_veto_problem_type_info(cls, session, request, response):
        """
        质控分析-强制拦截情况分析-问题所属类别分析
        :return:
        """
        target_name = "问题所属类别分析"
        data = cls.get_veto_sql_data(target_name, session, request)

        for item in data:
            if not item[1] or item[1] <= 0:
                continue
            protoData = {"data": []}  # response.targetData.add()
            protoData["yName"] = item[0] or ""
            protoData["targetName"] = target_name
            protoDataData = {}  # protoData.data.add()
            protoDataData["xData"] = item[0] or ""
            protoDataData["yData"] = str(item[1])
            protoData["data"].append(protoDataData)
            response["targetData"].append(protoData)

    @classmethod
    def get_veto_problem_num_info(cls, session, request, response):
        """
        质控分析-强制拦截情况分析-对应问题所属类别数量分析
        :return:
        """
        target_name = "特定类别问题数量分析"
        data = cls.get_veto_sql_data(target_name, session, request)
        first_name = "【%s】问题触发数量分析" % request.problemType

        y_names = ["问题数量"]
        cls.format_archive_response(y_names, response, first_name, data)

    @classmethod
    def get_refuse_sql_data(cls, target_name, session, request):
        """
        退回通用获取数据接口
        :return:
        """
        start_time = request.startTime
        end_time = request.endTime
        date_type = cls.get_date_type(start_time, end_time)
        branch = request.branch or "全部"
        if branch == "全部院区":
            branch = "全部"
        department = request.department or ""
        problemType = request.problemType or ""
        sql = '''call pr_case_qc_analyse_back('%s','%s','%s','%s','%s','%s','%s');''' % (
            target_name, department, branch, problemType, date_type, start_time, end_time)
        cls.logger.info("get_veto_sql_data, sql: %s", sql)
        query = session.execute(sql)
        data = query.fetchall()
        return data

    @classmethod
    def get_refuse_case_num_info(cls, session, request, response):
        """
        质控分析-病历退回情况分析-退回病历数、退回率
        :return:
        """
        target_name = "退回病历数"
        data = cls.get_refuse_sql_data(target_name, session, request)
        data = data[0]
        if len(data) == 1:
            data = cls.get_zero_data()
        target_list = ["退回病历数", "退回率"]

        for i in range(len(target_list)):
            protoInfo = {}  # response.targetInfo.add()
            protoInfo["name"] = target_list[i]
            protoInfo["count"] = str(data[i] or 0)
            protoInfo["sameCompareRate"] = str(data[i + 2] or 0)
            if target_list[i] == "退回率":
                protoInfo["count"] = cls.keep_one(data[i])
                protoInfo["sameCompareRate"] = cls.keep_one(data[i + 2])
                protoInfo["countSuffix"] = "%"
                protoInfo["sameCompareRate"] += "%"
            response["targetInfo"].append(protoInfo)

    @classmethod
    def get_refuse_ratio_info(cls, session, request, response):
        """
        质控分析-病历退回情况分析-病历退回率、退回病历数分析
        :return:
        """
        target_name = "病历退回率趋势分析"
        data = cls.get_refuse_sql_data(target_name, session, request)
        x_data = cls.get_x_data(request.startTime, request.endTime)
        y_info = {"病历退回率分析": ["病历退回率"], "退回病历数分析": ["退回病历数"]}
        cls.format_archive_x_response(response, data, y_info, x_data, keepOneFiled="病历退回率", suffixFields=["病历退回率"])

    @classmethod
    def get_refuse_dept_top_info(cls, session, request, response):
        """
        质控分析-病历退回情况分析-病历退回科室top10
        :return:
        """
        target_name = "病历退回率科室top10"
        data = cls.get_refuse_sql_data(target_name, session, request)
        y_names = ["病历退回率", "退回病历数"]
        cls.format_archive_response(y_names, response, target_name, data[:10], rate_y_name="病历退回率", suffixFields=["病历退回率"])

    @classmethod
    def get_refuse_doctor_top_info(cls, session, request, response, is_need_group):
        """
        质控分析-病历退回情况分析-对应科室重点关注医生top10
        :return:
        """
        target_name = "病历退回率重点关注医疗组" if is_need_group == 1 else "病历退回率重点关注医生top10"
        first_name = "【%s】重点关注%s" % (request.department, "医疗组" if is_need_group else "医生TOP10")
        data = cls.get_refuse_sql_data(target_name, session, request)
        if is_need_group != 1:
            data = data[:10]

        y_names = ["病历退回率", "退回病历数"]
        cls.format_archive_response(y_names, response, first_name, data, rate_y_name="病历退回率", suffixFields=["病历退回率"])

    @classmethod
    def get_refuse_problem_type_info(cls, session, request, response):
        """
        质控分析-病历退回情况分析-问题所属类别分析
        :return:
        """
        target_name = "问题所属类别分析"
        data = cls.get_refuse_sql_data(target_name, session, request)

        for item in data:
            if not item[1] or item[1] <= 0:
                continue
            protoData = {"data": []}  # response.targetData.add()
            protoData["yName"] = item[0] or ""
            protoData["targetName"] = target_name
            protoDataData = {}  # protoData.data.add()
            protoDataData["xData"] = item[0] or ""
            protoDataData["yData"] = str(item[1])
            protoData["data"].append(protoDataData)
            response["targetData"].append(protoData)

    @classmethod
    def get_refuse_problem_num_info(cls, session, request, response):
        """
        质控分析-病历退回情况分析-问题触发数量分析
        :return:
        """
        target_name = "特定类别问题数量分析"
        data = cls.get_refuse_sql_data(target_name, session, request)
        first_name = "【%s】问题触发数量分析" % request.problemType

        y_names = ["问题数量"]
        cls.format_archive_response(y_names, response, first_name, data)








