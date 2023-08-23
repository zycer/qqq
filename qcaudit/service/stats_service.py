# #!/usr/bin/env python
# # -*- coding:utf-8 -*-
# """
# @Author: zhangda@rxthinking.com
# @file: stats_service.py
# @time: 2021/7/2 9:48 上午
# @desc: 继承grpc生成的service类, 实现相关接口
# """
# import random
# import threading
# import time
# import traceback
# from datetime import datetime, timedelta
# import json
# import logging
# import os
# import uuid
# from collections import defaultdict
# from multiprocessing import Process
# from decimal import Decimal
# import arrow
# import pandas as pd
# import grpc
# from iyoudoctor.hosp.qc.v3.stats import FileData
# from iyoudoctor.hosp.qc.v3.stats.service_pb2_grpc_wrapper import StatsManagerServicer
# from iyoudoctor.hosp.qc.v3.stats.service_message_pb2 import GetStatsCaseApproveResponse, \
#     GetHospitalArchivingRateResponse, GetDepartmentArchivingRateResponse, GetDoctorArchivingRateResponse, \
#     GetDirectorArchivingRateResponse, GetMedicalIndicatorStatsResponse, GetStatsDepartmentScoreResponse, \
#     GetStatsCaseTargetResponse, GetStatsCaseDefectRateResponse, GetStatsCaseDefectCountResponse, \
#     GetStatsFlagCaseDefectListResponse, GetStatsCaseTagResponse, GetStatsDataUpdateStatusResponse, \
#     StatsDataUpdateResponse, GetDoctorArchivingRateCaseResponse, GetMedicalIndicatorStatsCaseResponse, \
#     GetFirstPageProblemsResponse, GetFirstPageScoreStatsResponse, GetFirstPageScoreDistributionResponse, \
#     CommonStatsResponse, GetFirstPageProblemConfigResponse, BatchCommonStatsResponse, \
#     GetProblemCategoryStatsResponse, GetCaseByProblemResponse, ExpertStatsPicCommonResponse, ExpertAllQcLevelResponse, \
#     CommonHeaderDataResponse, ExpertDeptScoreLevelResponse, ExpertDeptScoreDetailResponse, GetUpdateTimeResponse, \
#     GetProblemCategoryStatsResponse, GetCaseByProblemResponse, GetPatientPortraitResponse, GetStatsDiseaseDictResponse, \
#     CommonBatchResponse, GetStatsDiseaseOverviewResponse, GetStatsDiseaseOverviewMenuResponse, \
#     GetStatsDiseaseTargetDetailResponse, GetStatsDiseaseTargetDetailMenuResponse, GetStatsDiseaseContrastResponse, \
#     GetStatsReportDiseaseOverviewResponse, GetStatsReportRateResponse, GetStatsReportAgingResponse, \
#     GetBranchTimelinessRateDetailFormulaResponse, GetMonthArchivingRateResponse, StatsDefectRateListResponse, \
#     StatsDefectRateDetailListResponse, StatsCommonResponse, \
#     StatsArchivedQualityListResponse, StatsArchivedQualityDetailListResponse
# from openpyxl import Workbook
# from openpyxl.styles import Alignment, Font

# from qcaudit.common.const import QCITEM_CATEGORY, AI_DICT
# from qcaudit.config import Config
# from qcaudit.domain.problem.statsreq import GetProblemStatsRequest
# from qcaudit.domain.stats.archived_quality import ArchivedQualityStats
# from qcaudit.domain.stats.statsrepository import StatsRepository
# from qcaudit.service.protomarshaler import parseStatus, parseCaseStatus, parseStatusName
# from qcaudit.utils.bidataprocess import BIFormConfig, BIDataProcess
# from qcaudit.utils.towebconfig import *
# from qcaudit.service.protomarshaler import unmarshaldiseaseStatsDepartment, unmarshaldiseaseStatsTrend, \
#     unmarshaldiseaseContrastRadar, unmarshaldiseaseContrastTrend

# try:
#     from openpyxl.cell import get_column_letter, column_index_from_string
# except ImportError:
#     from openpyxl.utils import get_column_letter, column_index_from_string

# SortDict = {
#     "secondApply": 11,
#     "secondNoApply": 12,
#     "secondArchivingRate": 13,
#     "thirdApply": 14,
#     "thirdNoApply": 15,
#     "thirdArchivingRate": 16,
#     "seventhApply": 17,
#     "seventhNoApply": 18,
#     "seventhArchivingRate": 19,
#     "department": 0,
#     "applyCount": 3,
#     "dischargeCount": 2,
#     "refusedCount": 4,
#     "archivedCount": 5,
#     "unreviewCount": 6,
#     "archivingRate": 7,
#     "refusedRate": 8,
#     "finishRate": 9,
#     "imperfect": 10,
#     "timelyRate": 22,
#     "fixRate": 23,
# }


# class StatsService(StatsManagerServicer):
#     """
#     质控监管视窗统计接口服务类
#     """

#     def __init__(self, context):
#         self.context = context
#         self.logger = logging.getLogger("qcaudit.stats")
#         self.privateDataPath = "/tmp"
#         if not os.path.exists(self.privateDataPath):
#             os.makedirs(self.privateDataPath)

#     def StatsCaseRatio(self, request, context):
#         """
#         获取病历归档率、完成率、退回率、等级占比
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsCaseApproveResponse()
#         startTime, endTime = self.get_start_end_time(request)
#         if not startTime or not endTime:
#             return response

#         with self.context.app.mysqlConnection.session() as cursor:
#             stats_name_list = ['申请归档病历', '完成归档病历', '退回整改病历']
#             for stats_name in stats_name_list:
#                 call_approve_rate_sql = '''call pr_case_qc('%s','%s','%s', '')''' % (stats_name, startTime, endTime)
#                 query = cursor.execute(call_approve_rate_sql)
#                 self.logger.info("StatsCaseRatio, execute call_approve_rate_sql: %s", call_approve_rate_sql)
#                 queryset = query.fetchone()
#                 approve_case_count = queryset[0] or 0
#                 sameCompareRate = queryset[1] or 0.00
#                 chainCompareRate = queryset[2] or 0.00
#                 approve_rate = queryset[3] or 0.00

#                 proto_case_rate = response.caseRateInfo.add()
#                 proto_case_rate.statsName = stats_name
#                 proto_case_rate.count = int(approve_case_count)
#                 proto_case_rate.rate = self.keepOne(approve_rate)
#                 proto_case_rate.sameCompareRate = self.keepOne(sameCompareRate)
#                 proto_case_rate.chainCompareRate = self.keepOne(chainCompareRate)

#             stats_name = '病历等级占比分析'
#             call_level_rate_sql = '''call pr_case_qc('%s','%s','%s', '')''' % (stats_name, startTime, endTime)
#             self.logger.info("StatsCaseRatio, execute call_level_rate_sql: %s", call_level_rate_sql)
#             query = cursor.execute(call_level_rate_sql)
#             queryset = query.fetchall()
#             total = 0
#             first = 0
#             second = 0
#             third = 0
#             for item in queryset:
#                 count = item[1] or 0
#                 if item[0] == "甲":
#                     first += count
#                 if item[0] == "乙":
#                     second += count
#                 if item[0] == "丙":
#                     third += count
#                 total += count

#             proto_level_ratio = response.levelRatioInfo
#             proto_level_ratio.first = self.keepOne(first / total * 100) if total else self.keepOne(0)
#             proto_level_ratio.second = self.keepOne(second / total * 100) if total else self.keepOne(0)
#             proto_level_ratio.third = self.keepOne(third / total * 100) if total else self.keepOne(0)

#         return response

#     @classmethod
#     def keepOne(cls, a):
#         """
#         保留一位小数
#         :return:
#         """
#         return float("%.1f" % a)

#     def get_start_end_time(self, request):
#         """
#         将接收时间序列化为起始/终止时间
#         :return:
#         """
#         query_time = request.time or ""
#         timeType = request.timeType or ""
#         if not query_time or not timeType:
#             return None, None
#         if timeType == "quarter":
#             query_time_list = query_time.split(",")
#             if len(query_time_list) == 2:
#                 month_last_day = self.get_month_last_day(query_time)
#                 return "%s-01" % query_time_list[0], "%s-%s" % (query_time_list[1], month_last_day)
#             return None, None
#         month_last_day = self.get_month_last_day(query_time)
#         startTime = "%s-01-01" % query_time if timeType == "year" else "%s-01" % query_time
#         endTime = "%s-12-31" % query_time if timeType == "year" else "%s-%s" % (query_time, month_last_day)
#         if startTime > datetime.now().strftime("%Y-%m-%d"):
#             return None, None
#         return startTime, endTime

#     @classmethod
#     def get_month_last_day(cls, day):
#         """
#         获取月份最后一天
#         :param day:
#         :return:
#         """
#         year = int(day[:4])
#         if int(day[-2:]) in [4, 6, 9, 11]:
#             return 30
#         elif int(day[-2:]) == 2:
#             return 29 if (not year % 4 and year % 100) or not year % 400 else 28
#         return 31

#     def StatsDepartmentScore(self, request, context):
#         """
#         获取各科室质控成绩统计
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsDepartmentScoreResponse()
#         startTime, endTime = self.get_start_end_time(request)
#         if not startTime or not endTime:
#             return response

#         with self.context.app.mysqlConnection.session() as cursor:
#             stats_name = "各科室质控成绩统计"
#             call_department_score_sql = '''call pr_case_qc('%s','%s','%s', '')''' % (stats_name, startTime, endTime)
#             query = cursor.execute(call_department_score_sql)
#             self.logger.info("StatsDepartmentScore, execute call_department_score_sql: %s", call_department_score_sql)
#             queryset = query.fetchall()

#             for item in queryset:
#                 if not item[0]:
#                     continue
#                 protoItem = response.items.add()
#                 protoItem.departmentName = item[0]
#                 protoItem.firstNum = int(item[1] or 0)
#                 protoItem.secondNum = int(item[2] or 0)
#                 protoItem.thirdNum = int(item[3] or 0)
#                 protoItem.approveRatio = self.keepOne(item[4] or 0)
#                 protoItem.returnRatio = self.keepOne(item[5] or 0)

#         return response

#     def StatsCaseTarget(self, request, context):
#         """
#         获取病案指标统计
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsCaseTargetResponse()
#         startTime, endTime = self.get_start_end_time(request)
#         targetName = request.targetName or ""
#         if not startTime or not endTime:
#             return response
#         target_list = targetName.split(",")

#         with self.context.app.mysqlConnection.session() as cursor:
#             stats_name = "病案质量管理指标分析"
#             call_case_target_sql = '''call pr_case_qc('%s','%s','%s', '')''' % (stats_name, startTime, endTime)
#             query = cursor.execute(call_case_target_sql)
#             self.logger.info("StatsCaseTarget, execute call_case_target_sql: %s", call_case_target_sql)
#             queryset = query.fetchall()

#             parent_target_dict = {}
#             for item in queryset:
#                 parent_target = item[0]
#                 son_target = item[1]
#                 rate = self.keepOne(item[2] or 0)
#                 sameCompareRate = self.keepOne(item[3] or 0)
#                 chainCompareRate = self.keepOne(item[4] or 0)
#                 if targetName and parent_target not in target_list:
#                     self.logger.info("StatsCaseTarget, target_list is %s, parent_target is %s, not need show",
#                                      target_list, parent_target)
#                     continue
#                 if not parent_target_dict.get(parent_target, ""):
#                     protoItem = response.data.add()
#                     parent_target_dict[parent_target] = protoItem
#                     protoItem.parentTargetName = parent_target
#                 else:
#                     protoItem = parent_target_dict[parent_target]

#                 protoTarget = protoItem.targetData.add()
#                 protoTarget.sonTargetName = son_target
#                 protoTarget.rate = rate
#                 protoTarget.sameCompareRate = sameCompareRate
#                 protoTarget.chainCompareRate = chainCompareRate

#         return response

#     def StatsCaseDefectRate(self, request, context):
#         """
#         获取病历平均缺陷率
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsCaseDefectRateResponse()
#         startTime, endTime = self.get_start_end_time(request)
#         if not startTime or not endTime:
#             return response
#         today = datetime.now().strftime("%Y-%m-%d")
#         month = today[:-3]

#         with self.context.app.mysqlConnection.session() as cursor:
#             stats_name = "病历平均缺陷统计月分析" if request.timeType == "month" else "病历平均缺陷统计年分析"
#             call_case_defect_sql = '''call pr_case_qc('%s','%s','%s', '')''' % (stats_name, startTime, endTime)
#             query = cursor.execute(call_case_defect_sql)
#             self.logger.info("StatsCaseDefectRate, execute call_case_defect_sql: %s", call_case_defect_sql)
#             queryset = query.fetchall()

#             for item in queryset:
#                 if request.timeType == "month":
#                     if str(item[0][:-3]) > month or (str(item[0][:-3]) == month and str(item[0]) > today):
#                         # 大于当月或等于当月大于当天
#                         break
#                 else:
#                     if str(item[0]) > month:
#                         break

#                 protoItem = response.items.add()
#                 date = int(item[0][-2:])
#                 protoItem.xName = "{}号".format(date) if request.timeType == "month" else "{}月".format(date)
#                 protoItem.defectRate = self.keepOne(item[1] or 0)
#                 protoItem.firstPageDefectRate = self.keepOne(item[2] or 0)

#         return response

#     def StatsCaseDefectCount(self, request, context):
#         """
#         获取缺陷数量统计
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsCaseDefectCountResponse()
#         startTime, endTime = self.get_start_end_time(request)
#         if not startTime or not endTime:
#             return response
#         isFirstPage = request.isFirstPage

#         with self.context.app.mysqlConnection.session() as cursor:
#             stats_name = "常见缺陷发生数量统计"
#             call_case_defect_count_sql = '''call pr_case_qc('%s','%s','%s', '')''' % (stats_name, startTime, endTime)
#             query = cursor.execute(call_case_defect_count_sql)
#             self.logger.info("StatsCaseDefectCount, execute call_case_defect_count_sql: %s", call_case_defect_count_sql)
#             queryset = query.fetchall()
#             if queryset:
#                 for item in queryset:
#                     if isFirstPage == 0:
#                         protoItem = response.items.add()
#                         protoItem.defectName = item[0] or ""
#                         protoItem.nowCount = int(item[1] or 0)
#                         protoItem.pastCount = int(item[4] or 0)
#                     elif isFirstPage == 1:
#                         if item[2] != 0:
#                             protoItem = response.items.add()
#                             protoItem.defectName = item[0] or ""
#                             protoItem.nowCount = int(item[2] or 0)
#                             protoItem.pastCount = int(item[5] or 0)
#                     elif isFirstPage == 2:
#                         if item[3] != 0:
#                             protoItem = response.items.add()
#                             protoItem.defectName = item[0] or ""
#                             protoItem.nowCount = int(item[3] or 0)
#                             protoItem.pastCount = int(item[6] or 0)

#         return response

#     _FLAG_CASE_DEFECT_DICT = {}

#     def StatsFlagCaseDefectList(self, request, context):
#         """
#         获取重点病历缺陷分析
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsFlagCaseDefectListResponse()
#         startTime, endTime = self.get_start_end_time(request)
#         if not startTime or not endTime:
#             return response
#         sortTags = request.sortTags or []

#         self.update_tag_status_sort(sortTags)
#         self.query_flag_case_defect_by_thread(sortTags, startTime, endTime)

#         for case_flag in sortTags:
#             if case_flag.status != 1 or case_flag.name not in self._FLAG_CASE_DEFECT_DICT:
#                 continue
#             item = self._FLAG_CASE_DEFECT_DICT[case_flag.name]
#             protoItem = response.items.add()
#             protoItem.caseFlag = case_flag.name
#             protoItem.caseCount = int(item["caseCount"] or 0)
#             protoItem.defectCount = int(item["defectCount"] or 0)
#             protoItem.defectRate = self.keepOne(item["defectRate"] or 0)
#             protoItem.sameCompareRate = self.keepOne(item["sameCompareRate"] or 0)
#             protoItem.chainCompareRate = self.keepOne(item["chainCompareRate"] or 0)

#         return response

#     def query_flag_case_defect_by_thread(self, sortTags, startTime, endTime):
#         """
#         启动多线程
#         :return:
#         """
#         threads = []
#         for tag in sortTags:
#             if tag.status == 1:
#                 t = threading.Thread(target=self.thread_call_get_data, args=(startTime, endTime, tag.name))
#                 threads.append(t)

#         for t in threads:
#             t.setDaemon(True)
#             t.start()
#         for t in threads:
#             t.join()

#     def thread_call_get_data(self, startTime, endTime, name):
#         """
#         在存储过程获取病历缺陷数据线程函数
#         :return:
#         """
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_flag_case_sql = '''call pr_case_qc('重点病历缺陷分析','{}','{}', '{}')'''
#             query = cursor.execute(call_flag_case_sql.format(startTime, endTime, name))
#             queryset = query.fetchall()
#             if queryset:
#                 queryset = queryset[0]
#                 self._FLAG_CASE_DEFECT_DICT[queryset[0]] = {"caseCount": queryset[1], "defectCount": queryset[2],
#                                                             "defectRate": queryset[3], "sameCompareRate": queryset[5],
#                                                             "chainCompareRate": queryset[4]}

#     def update_tag_status_sort(self, sortTags):
#         """
#         更新重点病历标签状态和排序方式
#         :return:
#         """
#         query_old_tags_sql = '''select id, status, no from tags_qc'''
#         self.logger.info("update_tag_status_sort, query_old_tags_sql: %s", query_old_tags_sql)
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(query_old_tags_sql)
#             data = query.fetchall()
#         old_tags = {item[0]: [int(item[1]), int(item[2])] for item in data}
#         diff_tags = {item.id: [item.status, item.orderNo] for item in sortTags
#                      if item.status != old_tags[item.id][0] or item.orderNo != old_tags[item.id][1]}

#         self.logger.info("update_tag_status_sort, diff_tags: %s", diff_tags)
#         if diff_tags:
#             for tag_id in diff_tags:
#                 new_status = diff_tags[tag_id][0]
#                 new_orderNo = diff_tags[tag_id][1]
#                 update_sql = '''update tags_qc set status = "%s", no = "%s" where id = "%s"''' % (
#                     new_status, new_orderNo, tag_id)
#                 cursor.execute(update_sql)
#             cursor.commit()

#     def GetStatsCaseTag(self, request, context):
#         """
#         获取病历标签字典
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsCaseTagResponse()
#         query_name = request.input or ""

#         with self.context.app.mysqlConnection.session() as cursor:
#             query_tag_sql = '''select * from tags_qc'''
#             if query_name:
#                 query_tag_sql += ''' where name like "%{}%"'''.format(query_name)
#             query_tag_sql += ''' order by no'''
#             self.logger.info("GetStatsCaseTag, execute query_tag_sql: %s", query_tag_sql)
#             query = cursor.execute(query_tag_sql)
#             data = query.fetchall()

#             for item in data:
#                 protoItem = response.data.add()
#                 protoItem.id = item[0]
#                 protoItem.name = item[1] or ""
#                 protoItem.code = item[2] or ""
#                 protoItem.status = int(item[3])
#                 protoItem.orderNo = int(item[4])

#         return response

#     def StatsTableUpdate(self, request, context):
#         """
#         数据更新
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsDataUpdateResponse()

#         result = self.getLastUpdateTime(request.type)
#         can_update_time = datetime.now() + timedelta(hours=8) - timedelta(minutes=5)
#         self.logger.info("StatsTableUpdate, can_update_time: %s", can_update_time)
#         if result.get("updateTime", "") and result.get("updateTime") > can_update_time:
#             response.isSuccess = False
#             response.message = "数据更新频率太高"
#             return response

#         with self.context.app.mysqlConnection.session() as cursor:
#             table = self.get_update_status_table(request.type)
#             update_this_time_sql = "update %s set updatestatus = 1, updatetime = Now();" % table
#             ret = cursor.execute(update_this_time_sql)
#             cursor.commit()
#             self.logger.info("StatsDataUpdate, update_this_time_sql: %s", update_this_time_sql)
#             if ret:
#                 try:
#                     p = threading.Thread(target=self.finishTableUpdate, args=(request.type, ))
#                     p.start()
#                     response.isSuccess = True
#                 except Exception:
#                     response.isSuccess = False
#                     response.message = "更新失败"
#                     self.logger.error("StatsDataUpdate, finishTableUpdate, error: %s", traceback.format_exc())

#         return response

#     def finishTableUpdate(self, u_type):
#         """
#         更新数据进程函数
#         :return:
#         """
#         if u_type == "expert":
#             call_update_data_sql = '''call pr_case_expert_process("2010-01-01","2030-12-31")'''
#         elif u_type == "archive":
#             call_update_data_sql = '''call pr_case_archiverate_process("", "")'''
#         elif u_type in ("running", "veto", "refuse"):
#             call_update_data_sql = '''call pr_case_qc_analyse_process('','');'''
#         elif u_type == "workload":
#             call_update_data_sql = '''call pr_case_report_process('','');'''
#         else:
#             call_update_data_sql = '''call pr_case_qc_process("", "")'''
#         with self.context.app.mysqlConnection.session() as cursor:
#             self.logger.info("finishTableUpdate, call_update_data_sql: %s", call_update_data_sql)
#             cursor.execute(call_update_data_sql)
#             cursor.commit()

#     def GetStatsTableUpdateStatus(self, request, context):
#         """
#         统计数据更新状态信息
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsDataUpdateStatusResponse()

#         result = self.getLastUpdateTime(request.type)
#         response.status = result.get("status", 0)
#         updateDatetime = result.get("updateTime", "")
#         self.logger.info("lastUpdateTime: %s", updateDatetime)
#         response.lastUpdateTime = updateDatetime.strftime('%Y-%m-%d %H:%M:%S') if updateDatetime else ""
#         return response

#     @classmethod
#     def get_update_status_table(cls, u_type):
#         """
#         获取更新状态、时间表名
#         :return:
#         """
#         table = "case_updatestatus_qc"
#         if u_type in ("hospital", "table"):
#             table = "case_updatestatus_qc"
#         elif u_type == "archive":
#             table = "case_updatestatus"
#         elif u_type == "expert":
#             table = "case_updatestatus_expert"
#         elif u_type in ("running", "veto", "refuse"):
#             table = "case_qc_analyse_updatestatus"
#         elif u_type == "workload":
#             table = "case_report_updatestatus"
#         return table

#     def getLastUpdateTime(self, u_type):
#         """
#         查询上次更新时间
#         :return:
#         """
#         result = {}
#         with self.context.app.mysqlConnection.session() as cursor:
#             table = self.get_update_status_table(u_type)
#             query_last_update_time_sql = "select updatetime, updatestatus from %s" % table
#             query = cursor.execute(query_last_update_time_sql)
#             self.logger.info("getLastUpdateTime, query_last_update_time_sql: %s", query_last_update_time_sql)
#             ret = query.fetchone()
#             if ret:
#                 result["status"] = int(ret[1] or 0)
#                 updateDatetime = ret[0] + timedelta(hours=8) if ret[0] else ""
#                 self.logger.info("getLastUpdateTime, updateDatetime: %s", updateDatetime)
#                 result["updateTime"] = updateDatetime
#         return result

#     def GetHospitalArchivingRate(self, request, context):
#         """
#         统计全院归档率
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetHospitalArchivingRateResponse()

#         branch = request.branch or "全部"
#         args = [request.startTime, request.endTime, 'hospital', branch, '全部', "全部", ""]
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = """call pr_case_archiverate('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             for item in queryset:
#                 protoItem = response.data.add()
#                 protoItem.branch = item[0] or ""
#                 protoItem.dischargeCount = int(item[1] or 0)
#                 protoItem.applyCount = int(item[2] or 0)
#                 protoItem.refusedCount = int(item[3] or 0)
#                 protoItem.archivedCount = int(item[4] or 0)
#                 protoItem.unreviewCount = int(item[5] or 0)
#                 protoItem.archivingRate = float(item[6] or 0)
#                 protoItem.refusedRate = float(item[7] or 0)
#                 protoItem.finishRate = float(item[8] or 0)
#                 protoItem.imperfect = float(item[9] or 0)
#                 protoItem.secondApply = int(item[10] or 0)
#                 protoItem.secondNoApply = int(item[11] or 0)
#                 protoItem.secondArchivingRate = float(item[12] or 0)
#                 protoItem.thirdApply = int(item[13] or 0)
#                 protoItem.thirdNoApply = int(item[14] or 0)
#                 protoItem.thirdArchivingRate = float(item[15] or 0)
#                 protoItem.seventhApply = int(item[16] or 0)
#                 protoItem.seventhNoApply = int(item[17] or 0)
#                 protoItem.seventhArchivingRate = float(item[18] or 0)

#                 protoItem.timelyRate = str(item[19] if item[19] else 0)
#                 protoItem.fixRate = str(item[20] if item[20] else 0)

#         return response

#     def GetDepartmentArchivingRate(self, request, context):
#         """
#         统计科室归档率
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDepartmentArchivingRateResponse()
#         sizeCount = 0

#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         args = [request.startTime, request.endTime, 'dept', branch, department, "全部", ""]
#         is_need_summary = int(self.context.app.config.get(Config.QC_STATS_DEPT_ARCHIVE) or 0)

#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = """call pr_case_archiverate('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             print("call_proc_sql", call_proc_sql)
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             # 科室归档率排序
#             sortedResult = self.sortDepartmentArchivingRateResult(queryset)
#             for item in sortedResult:
#                 if is_need_summary != 1 and "汇总" in (item[0] or ""):
#                     continue
#                 sizeCount += 1
#                 protoItem = response.data.add()
#                 # protoItem.branch = item[0] if item[0] else ""
#                 protoItem.department = item[0] or ""
#                 # protoItem.doctor = item[1] if item[1] else ""
#                 protoItem.dischargeCount = int(item[1]) if item[1] else 0
#                 protoItem.applyCount = int(item[2]) if item[2] else 0
#                 protoItem.refusedCount = int(item[3]) if item[3] else 0
#                 protoItem.archivedCount = int(item[4]) if item[4] else 0
#                 protoItem.unreviewCount = int(item[5]) if item[5] else 0
#                 protoItem.archivingRate = float(item[6]) if item[6] else 0
#                 protoItem.refusedRate = float(item[7]) if item[7] else 0
#                 protoItem.finishRate = float(item[8]) if item[8] else 0
#                 protoItem.imperfect = float(item[9]) if item[9] else 0

#                 protoItem.secondApply = int(item[10]) if item[10] else 0
#                 protoItem.secondNoApply = int(item[11]) if item[11] else 0
#                 protoItem.secondArchivingRate = float(item[12]) if item[12] else 0
#                 protoItem.thirdApply = int(item[13]) if item[13] else 0
#                 protoItem.thirdNoApply = int(item[14]) if item[14] else 0
#                 protoItem.thirdArchivingRate = float(item[15]) if item[15] else 0
#                 protoItem.seventhApply = int(item[16]) if item[16] else 0
#                 protoItem.seventhNoApply = int(item[17]) if item[17] else 0
#                 protoItem.seventhArchivingRate = float(item[18]) if item[18] else 0

#                 protoItem.timelyRate = str(item[19] if item[19] else 0)
#                 protoItem.fixRate = str(item[20] if item[20] else 0)

#         return response

#     @classmethod
#     def sortDepartmentArchivingRateResult(cls, queryset, sortWay="asc"):
#         """
#         科室归档率结果排序
#         :param queryset:
#         :param sortWay:
#         :return:
#         """
#         resultList = [queryset[0]]
#         deptDict = defaultdict(list)
#         for item in queryset[1:]:
#             # 同一科室的排序号相同，根据排序号分组
#             deptDict[item[-1]].append(item)

#         deptList = list(deptDict.items())

#         if sortWay == "desc":
#             sortedDept = sorted(deptList, key=lambda x: (x[0] or 0), reverse=True)
#         else:
#             sortedDept = sorted(deptList, key=lambda x: (x[0] or 0))
#         for item in sortedDept:
#             if sortWay == "desc":
#                 sortedRows = sorted(item[1] or "-", key=lambda x: (2 if x[0] and x[0].endswith(u"汇总") else 1), reverse=True)
#             else:
#                 sortedRows = sorted(item[1] or "-", key=lambda x: (0 if x[0] and x[0].endswith(u"汇总") else 1))
#             resultList.extend(sortedRows)

#         return resultList

#     @classmethod
#     def getFileId(cls):
#         """
#         获取文件id
#         :return:
#         """
#         return uuid.uuid4().hex

#     def ExportDepartmentArchivingRate(self, request, context):
#         """
#         导出科室归档率
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()

#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         args = [request.startTime, request.endTime, 'dept', branch, department, '全部', ""]

#         excelTitle = "{0}至{1}各科室病历完成情况".format(request.startTime, request.endTime)
#         exportName = "科室归档率{0}至{1}.xlsx".format(request.startTime, request.endTime)
#         is_need_summary = int(self.context.app.config.get(Config.QC_STATS_DEPT_ARCHIVE) or 0)
#         with self.context.app.mysqlConnection.session() as cursor:
#             fileId = self.getFileId()
#             filename = "%s.xlsx" % fileId
#             fullname = os.path.join(self.privateDataPath, filename)
#             wb = Workbook()
#             call_proc_sql = """call pr_case_archiverate('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             self.logger.info("call_proc_sql: %s", json.dumps(call_proc_sql, ensure_ascii=False))
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             retCols = query.keys()
#             if queryset:
#                 sortedResult = self.sortDepartmentArchivingRateResult(queryset)
#                 self.generateWorkSheet(sortedResult, wb, retCols, title=excelTitle, exportType="department", is_need_summary=is_need_summary)
#             wb.save(fullname)
#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     @classmethod
#     def generateWorkSheet(cls, queryset, wb, retCols, title="", exportType="doctor", enableFR=False, is_need_summary=1):
#         """
#         数据写入excel
#         :return:
#         """
#         # ws = wb.create_sheet(u"病历统计")
#         ws = wb.active
#         # ws.title = u""
#         colLen = len(retCols) - 1

#         titleResult = [retCols[0], retCols[1]]
#         if enableFR:
#             titleResult.append(retCols[20])
#         else:
#             colLen = colLen - 1
#         colLetter = get_column_letter(colLen)
#         mergeStr = "A1:%s1" % colLetter
#         ws.merge_cells(mergeStr)
#         ws["A1"] = title
#         alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
#         ws["A1"].alignment = alignment

#         titleResult.extend(retCols[11:20])
#         if exportType == "doctor":
#             titleResult.extend(retCols[22: 24])
#         else:
#             titleResult.extend(retCols[20: 21])
#         titleResult.extend(retCols[2:11])
#         ws.append(tuple(titleResult))
#         tmp_list = []
#         if exportType == "doctor":
#             if enableFR:
#                 for row_queryset in queryset:
#                     r = row_queryset
#                     if (r[0], r[1]) in tmp_list:
#                         continue
#                     tmp_list.append((r[0], r[1]))
#                     if r[20] and r[21] and r[20] != "--":
#                         tempDoctorFR = "{0}{1}".format(r[20], r[21])
#                     else:
#                         tempDoctorFR = r[20]
#                     tempDoctorFR = tempDoctorFR if tempDoctorFR else ""
#                     timelyRate = "{:.2f}%".format(r[22]) if r[22] != "-" else r[22]
#                     fixRate = "{:.2f}%".format(r[23]) if r[23] != "-" else r[23]
#                     retRow = [r[0], r[1], tempDoctorFR, r[11], r[12], "{:.2f}%".format(r[13]), r[14], r[15],
#                             "{:.2f}%".format(r[16]), r[17], r[18], timelyRate, fixRate, r[2], r[3], r[4], r[5], r[6],
#                             "{:.2f}%".format(r[7]), "{:.2f}%".format(r[8]), "{:.2f}%".format(r[9]), r[10]]
#                     ws.append(tuple(retRow))
#             else:
#                 for row_queryset in queryset:
#                     r = row_queryset
#                     if (r[0], r[1]) in tmp_list:
#                         continue
#                     tmp_list.append((r[0], r[1]))
#                     timelyRate = "{:.2f}%".format(float(r[22])) if r[22] != "-" else r[22]
#                     fixRate = "{:.2f}%".format(float(r[23])) if r[23] != "-" else r[23]
#                     retRow = [r[0], r[1], r[11], r[12], "{:.2f}%".format(r[13]), r[14], r[15], "{:.2f}%".format(r[16]),
#                               r[17], r[18], "{:.2f}%".format(r[19]), timelyRate, fixRate, r[2], r[3], r[4], r[5], r[6],
#                               "{:.2f}%".format(r[7]), "{:.2f}%".format(r[8]), "{:.2f}%".format(r[9]), r[10]]
#                     ws.append(tuple(retRow))
#         else:
#             for row_queryset in queryset:
#                 r = row_queryset
#                 if is_need_summary != 1 and "汇总" in (r[0] or ""):
#                     continue
#                 if (r[0], r[1]) in tmp_list:
#                     continue
#                 tmp_list.append((r[0], r[1]))
#                 # print "row type is : %s" % type(row_queryset[1:-1])
#                 rowData = list(row_queryset[:-1])
#                 rowData[6] = "{:.2f}%".format(rowData[6])
#                 rowData[7] = "{:.2f}%".format(rowData[7])
#                 rowData[8] = "{:.2f}%".format(rowData[8])
#                 rowData[12] = "{:.2f}%".format(rowData[12])
#                 rowData[15] = "{:.2f}%".format(rowData[15])
#                 rowData[18] = "{:.2f}%".format(rowData[18])
#                 rowData[19] = "{:.2f}%".format(float(rowData[19])) if rowData[19] != "-" else rowData[19]
#                 rowData[20] = "{:.2f}%".format(float(rowData[20])) if rowData[20] != "-" else rowData[20]

#                 tmp = rowData[:2] + rowData[11: 21] + rowData[2: 11]
#                 ws.append(tuple(tmp))

#     @classmethod
#     def getRequestStartAndSize(cls, request):
#         """
#         获取分页请求中的start和size
#         :return:
#         """
#         size = 10
#         start = 0
#         MAXSIZE = 1000
#         if request.size and 0 < request.size <= MAXSIZE:
#             size = request.size
#         if request.size > MAXSIZE:
#             size = MAXSIZE
#         if request.start:
#             start = request.start
#         return start, size

#     def GetDoctorArchivingRate(self, request, context):
#         """
#         统计医生归档率
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorArchivingRateResponse()
#         sizeCount = 0
#         start, size = self.getRequestStartAndSize(request)
#         current = 0
#         # startDate = request.startTime.ToDatetime()
#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         doctor = request.doctor or "全部"
#         doctorFR = request.doctorFR or "全部"
#         args = [request.startTime, request.endTime, 'doctor', branch, department, doctor, doctorFR]
#         sortKey = SortDict[request.sortKey] if request.sortKey else 19

#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = """call pr_case_archiverate('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("GetDoctorArchivingRate, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             totalCount = sum([1 for item in queryset if not item[21]])
#             if queryset:
#                 # sort result:
#                 # 过滤掉F/R列
#                 if not request.enableFR:
#                     filter(lambda x: x[20] == "--", queryset)
#                 sortedResult = self.sortArchivingRateResult(queryset, sortKey, request.sortWay)
#                 tmp_list = []
#                 for item in sortedResult:
#                     if (item[0], item[1]) in tmp_list:
#                         continue
#                     tmp_list.append((item[0], item[1]))
#                     current += 1
#                     if current <= start:
#                         continue
#                     # 控制分页
#                     if current > start + size:
#                         break
#                     else:
#                         sizeCount += 1
#                         protoItem = response.data.add()
#                         # protoItem.branch = item[0] if item[0] else ""
#                         protoItem.department = item[0] if item[0] else ""
#                         protoItem.doctor = item[1] if item[1] else ""
#                         protoItem.dischargeCount = int(item[2]) if item[2] else 0
#                         protoItem.applyCount = int(item[3]) if item[3] else 0
#                         protoItem.refusedCount = int(item[4]) if item[4] else 0
#                         protoItem.archivedCount = int(item[5]) if item[5] else 0
#                         protoItem.unreviewCount = int(item[6]) if item[6] else 0
#                         protoItem.archivingRate = float(item[7]) if item[7] else 0
#                         protoItem.refusedRate = float(item[8]) if item[8] else 0
#                         protoItem.finishRate = float(item[9]) if item[9] else 0
#                         protoItem.imperfect = float(item[10]) if item[10] else 0

#                         protoItem.secondApply = int(item[11]) if item[11] else 0
#                         protoItem.secondNoApply = int(item[12]) if item[12] else 0
#                         protoItem.secondArchivingRate = float(item[13]) if item[13] else 0
#                         protoItem.thirdApply = int(item[14]) if item[14] else 0
#                         protoItem.thirdNoApply = int(item[15]) if item[15] else 0
#                         protoItem.thirdArchivingRate = float(item[16]) if item[16] else 0
#                         protoItem.seventhApply = int(item[17]) if item[17] else 0
#                         protoItem.seventhNoApply = int(item[18]) if item[18] else 0
#                         protoItem.seventhArchivingRate = float(item[19]) if item[19] else 0
#                         protoItem.doctorFR = item[20] if item[20] else ""
#                         protoItem.doctorFRFlag = item[21] if item[21] else ""

#                         protoItem.timelyRate = str(item[22] if item[22] else 0)
#                         protoItem.fixRate = str(item[23] if item[23] else 0)

#         response.total = totalCount
#         response.size = sizeCount
#         response.start = start
#         return response

#     def sortArchivingRateResult(self, queryset, sortKey, sortWay):
#         """
#         医生归档率结果排序
#         :return:
#         """
#         resultList = [queryset[0]]
#         deptDict = defaultdict(list)
#         for item in queryset[1:]:
#             deptDict[item[0]].append(item)

#         deptList = list(deptDict.items())
#         try:
#             if sortWay == "desc":
#                 sortedDept = sorted(deptList, key=lambda x: self.getDeptsSortVal(x, deptDict)[sortKey] or 0, reverse=True)
#             else:
#                 sortedDept = sorted(deptList, key=lambda x: self.getDeptsSortVal(x, deptDict)[sortKey] or 0)
#         except TypeError:
#             self.logger.error("sortArchivingRateResult, error: %s", traceback.format_exc())
#             sortedDept = deptList
#         for item in sortedDept:
#             if sortWay == "desc":
#                 # x[20]是指F/R
#                 sortedRows = sorted(item[1] or 0,
#                                     key=lambda x: (2 if (x[1] or "-") == "--" else 1, x[1] or "-", 2 if (x[20] or "-") == "--" else 1, x[sortKey]or 0),
#                                     reverse=True)
#             else:
#                 sortedRows = sorted(item[1] or 0,
#                                     key=lambda x: (0 if (x[1] or "-") == "--" else 1, x[1] or "-", 0 if (x[20] or "-") == "--" else 1, x[sortKey] or 0))
#             resultList.extend(sortedRows)

#         return resultList

#     def getDeptsSortVal(self, deptsListItem, deptDict):
#         """
#         从sortArchivingRateResult 的deptsList 获取外层科室排序的对应值
#         :return:
#         """
#         dept = deptsListItem[0]
#         result = deptDict[dept][0] or "-"
#         flag = False
#         for item in deptDict[dept]:
#             if item[1] == "--":
#                 result = item
#                 flag = True
#                 break
#         if not flag:
#             self.logger.info("department %s has no total stats!" % dept)

#         return result

#     def ExportDoctorArchivingRate(self, request, context):
#         """
#         导出医生归档率
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()
#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         doctor = request.doctor or "全部"
#         doctorFR = request.doctorFR or "全部"
#         args = [request.startTime, request.endTime, 'doctor', branch, department, doctor, doctorFR]
#         sortKey = SortDict[request.sortKey] if request.sortKey else 19

#         excelTitle = "{0}至{1}各ATTENDING组出院病人病历完成情况".format(request.startTime, request.endTime)
#         exportName = "医生归档率{0}至{1}.xlsx".format(request.startTime, request.endTime)
#         with self.context.app.mysqlConnection.session() as cursor:
#             fileId = self.getFileId()
#             filename = "%s.xlsx" % fileId
#             fullname = os.path.join(self.privateDataPath, filename)
#             wb = Workbook()
#             call_proc_sql = """call pr_case_archiverate('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("ExportDoctorArchivingRate, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             retCols = query.keys()
#             if queryset:
#                 if not request.enableFR:
#                     filter(lambda item: item[20] == "--", queryset)
#                 sortedResult = self.sortArchivingRateResult(queryset, sortKey, request.sortWay)
#                 self.generateWorkSheet(sortedResult, wb, retCols, title=excelTitle, enableFR=request.enableFR)
#             wb.save(fullname)

#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     def GetDirectorArchivingRate(self, request, context):
#         """
#         获取科主任统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDirectorArchivingRateResponse()
#         sizeCount = 0
#         start, size = self.getRequestStartAndSize(request)
#         current = 0
#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         args = [request.startTime, request.endTime, branch, department]
#         # sortKey = SortDict[request.sortKey] if request.sortKey else 7
#         # 只根据序号Id来排序
#         sortKey = 7
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = """call pr_case_aindex('%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("GetDirectorArchivingRate, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             totalCount = len(queryset)
#             if queryset:
#                 # sort result:
#                 sortedResult = self.sortDirectorStatsResult(queryset, sortKey, request.sortWay)
#                 for item in sortedResult:
#                     current += 1
#                     if current <= start:
#                         continue
#                     # 控制分页
#                     if current > start + size:
#                         break
#                     else:
#                         sizeCount += 1
#                         protoItem = response.data.add()
#                         # protoItem.branch = item[0] if item[0] else ""
#                         protoItem.department = item[0] if item[0] else ""
#                         protoItem.doctor = item[1] if item[1] else ""
#                         protoItem.dischargeCount = int(item[2]) if item[2] else 0
#                         protoItem.primaryDiagValidRate = float(item[3]) if item[3] else 0
#                         protoItem.minorDiagValidRate = float(item[4]) if item[4] else 0
#                         protoItem.primaryOperValidRate = float(item[5]) if item[5] else 0
#                         protoItem.minorOperValidRate = float(item[6]) if item[6] else 0

#         response.total = totalCount
#         response.size = sizeCount
#         response.start = start
#         return response

#     def sortDirectorStatsResult(self, queryset, sortKey, sortWay="asc"):
#         """
#         科主任统计结果排序
#         :return:
#         """
#         resultList = [queryset[0]]
#         deptDict = defaultdict(list)
#         for item in queryset[1:]:
#             deptDict[item[0]].append(item)

#         deptList = list(deptDict.items())

#         if sortWay == "desc":
#             sortedDept = sorted(deptList, key=lambda x: self.getDeptsSortVal(x, deptDict)[sortKey], reverse=True)
#         else:
#             sortedDept = sorted(deptList, key=lambda x: self.getDeptsSortVal(x, deptDict)[sortKey])
#         for item in sortedDept:
#             if sortWay == "desc":
#                 sortedRows = sorted(item[1] or "-", key=lambda x: (2 if (x[1] or "-") == "--" else 1, x[1] or "-"), reverse=True)
#             else:
#                 sortedRows = sorted(item[1] or "-", key=lambda x: (0 if (x[1] or "-") == "--" else 1, x[1] or "-"))
#             resultList.extend(sortedRows)

#         return resultList

#     def ExportDirectorArchivingRate(self, request, context):
#         """
#         导出科主任统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()

#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         args = [request.startTime, request.endTime, branch, department]
#         sortKey = 7

#         excelTitle = "{0}至{1}科主任指标统计".format(request.startTime, request.endTime)
#         exportName = "{0}至{1}科主任指标统计.xlsx".format(request.startTime, request.endTime)
#         with self.context.app.mysqlConnection.session() as cursor:
#             fileId = self.getFileId()
#             filename = "%s.xlsx" % fileId
#             fullname = os.path.join(self.privateDataPath, filename)
#             wb = Workbook()
#             call_proc_sql = """call pr_case_aindex('%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             retCols = query.keys()
#             if queryset:
#                 totalCount = len(queryset)
#                 self.logger.info("totalCount is : %s" % totalCount)
#                 sortedResult = self.sortDirectorStatsResult(queryset, sortKey, request.sortWay)
#                 self.generateDirectorWorkSheet(sortedResult, wb, retCols, title=excelTitle)
#             wb.save(fullname)
#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     @classmethod
#     def generateDirectorWorkSheet(cls, queryset, wb, retCols, title=""):
#         """
#         科主任统计导出写入excel
#         :return:
#         """
#         ws = wb.active
#         colLen = len(retCols)
#         colLetter = get_column_letter(colLen)
#         mergeStr = "A1:%s1" % colLetter
#         ws.merge_cells(mergeStr)
#         ws["A1"] = title
#         alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
#         ws["A1"].alignment = alignment
#         ws.append(tuple(retCols))
#         for row_queryset in queryset:
#             rowData = list(row_queryset[:-1])
#             rowData[3] = "{:.2f}%".format(rowData[3])
#             rowData[4] = "{:.2f}%".format(rowData[4])
#             rowData[5] = "{:.2f}%".format(rowData[5])
#             rowData[6] = "{:.2f}%".format(rowData[6])
#             ws.append(tuple(rowData))

#     def ExportDirectorArchivingRateCase(self, request, context):
#         """
#         导出科主任统计病历详情病历
#         :return:
#         """
#         response = FileData()
#         queryset, totalCount, start = self.query_docror_archiving_data(request)

#         fileId = uuid.uuid4().hex
#         filename = "%s.xlsx" % fileId
#         fullname = os.path.join(self.privateDataPath, filename)
#         exportName = "{0}至{1}科主任指标统计明细.xlsx".format(request.startTime, request.endTime)

#         wb = Workbook()
#         patient_id_name = self.context.app.config.get(Config.QC_PATIENT_ID_NAME)
#         titles = [patient_id_name, "姓名", "入院日期", "出院日期", "出院科室", "医生", "住院天数",
#                   "首页主诊断是否正确", "首页次诊断是否完整", "首页主手术/操作填写是否准确", "首页次手术/操作填写是否完整"]
#         ws = wb.active
#         ws.append(tuple(titles))

#         for item in queryset:
#             rowData = []
#             rowData.append(item[2] if item[2] else "")
#             rowData.append(item[3] if item[3] else "")
#             rowData.append(item[9].strftime("%Y-%m-%d") if item[9] else "")
#             rowData.append(item[10].strftime("%Y-%m-%d") if item[10] else "")
#             rowData.append(item[7] if item[7] else "")
#             rowData.append(item[8] if item[8] else "")
#             rowData.append(item[12] if item[12] else "0")
#             rowData.append(item[24] if item[24] else "")
#             rowData.append(item[25] if item[25] else "")
#             rowData.append(item[26] if item[26] else "")
#             rowData.append(item[27] if item[27] else "")
#             ws.append(tuple(rowData))
#         wb.save(fullname)
#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     def query_docror_archiving_data(self, request):
#         """
#         查询医生(科主任)归档率明细数据
#         :return:
#         """
#         start, size = self.getRequestStartAndSize(request)
#         conditionStr = ""
#         params = []
#         # 构造查询条件
#         if request.startTime:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.dischargeTime >= '%s' "
#             params.append(request.startTime)
#         # 出院结束时间
#         if request.endTime:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.dischargeTime <= '%s' "
#             if len(request.endTime) <= 10:
#                 params.append(request.endTime + " 23:59:59")
#             else:
#                 params.append(request.endTime)
#         if request.branch:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.branch = '%s' "
#             params.append(request.branch)
#         if request.department:
#             deptList = request.department.split(",")
#             formatStr = ",".join(['"%s"' % item for item in deptList])
#             conditionStr += (" and " if conditionStr != "" else "") + " c.outDeptName in (%s)" % formatStr
#         if request.doctor and request.doctor != "--":
#             doctorList = request.doctor.split(",")
#             doctorListStr = ",".join(['"%s"' % item for item in doctorList])
#             conditionStr += (" and " if conditionStr != "" else "") + " c.attendDoctor in (%s) " % doctorListStr
#         if hasattr(request, "applyFlag") and request.applyFlag:
#             conditionStr += (" and " if conditionStr != "" else "") + " cx.applyflag = '%s' "
#             params.append(request.applyFlag)
#         if hasattr(request, "reviewFlag") and request.reviewFlag:
#             conditionStr += (" and " if conditionStr != "" else "") + " cx.auditflag = '%s' "
#             params.append(request.reviewFlag)
#         if hasattr(request, "isPrimaryDiagValid") and request.isPrimaryDiagValid:
#             conditionStr += (" and " if conditionStr != "" else "") + " cx.isprimarydiagvalid = '%s' "
#             params.append(request.isPrimaryDiagValid)
#         if hasattr(request, "isMinorDiagValid") and request.isMinorDiagValid:
#             conditionStr += (" and " if conditionStr != "" else "") + " cx.isminordiagvalid = '%s' "
#             params.append(request.isMinorDiagValid)
#         if hasattr(request, "isPrimaryOperValid") and request.isPrimaryOperValid:
#             conditionStr += (" and " if conditionStr != "" else "") + " cx.isprimaryopervalid = '%s' "
#             params.append(request.isPrimaryOperValid)
#         if hasattr(request, "isMinorOperValid") and request.isMinorOperValid:
#             conditionStr += (" and " if conditionStr != "" else "") + " cx.isminoropervalid = '%s' "
#             params.append(request.isMinorOperValid)
#         if hasattr(request, "doctorFR") and request.doctorFR:
#             if request.doctorFRFlag == "F":
#                 conditionStr += (" and " if conditionStr != "" else "") + " cx.fellowdoctor = '%s' "
#                 params.append(request.doctorFR)
#             elif request.doctorFRFlag == "R":
#                 conditionStr += (" and " if conditionStr != "" else "") + " cx.residentdoctor = '%s' "
#                 params.append(request.doctorFR)
#             else:
#                 conditionStr += (" and " if conditionStr != "" else "") \
#                                 + " ( FIND_IN_SET(cx.residentdoctor, '%s') or FIND_IN_SET(cx.fellowdoctor, '%s')) "
#                 params.append(request.doctorFR)
#                 params.append(request.doctorFR)

#         if conditionStr:
#             conditionStr = " where " + conditionStr

#         # 排序规则
#         if request.sortKey:
#             if request.sortKey not in ["inpDays", "dischargeTime", "caseId", "admitTime"]:
#                 self.logger.error("sortKey is not support.")
#                 return None, None, None
#         if request.sortWay:
#             if request.sortWay.lower() not in ["asc", "desc", "null"]:
#                 self.logger.error("sortWay is not support.")
#                 return None, None, None
#         sort = (request.sortKey if request.sortKey else "dischargeTime") + " " + (
#             request.sortWay if request.sortWay and request.sortWay != "null" else "ASC")

#         # get case list,一共30个字段
#         with self.context.app.mysqlConnection.session() as cursor:
#             # get total count
#             query_count_sql = """select count(id) from `case` as c join case_extend cx on c.caseId = cx.caseid 
#                     left join dim_dept_statis d on c.outDeptId = d.deptid """ + (conditionStr if conditionStr else "")
#             query_count_sql = query_count_sql % tuple(params)
#             self.logger.info("GetDoctorArchivingRateCase, query_count_sql: %s", query_count_sql)
#             query = cursor.execute(query_count_sql)
#             ret = query.fetchone()
#             totalCount = ret[0]

#             query_data_sql = """select id, c.caseId,c.patientId, c.name, c.gender, c.hospital, c.branch,
#                           c.outDeptName, c.attendDoctor, c.admitTime,c.dischargeTime,cx.outdeptname,
#                           c.inpDays, cx.applyflag, c.applytime, c.applyDoctor,cx.auditflag, c.reviewer, c.reviewTime,
#                           c.isDead, cx.isSecondArchiving, cx.isThirdArchiving, cx.isSeventhArchiving, c.hasOutDeptProblem ,
#                           cx.isprimarydiagvalid, cx.isminordiagvalid, cx.isprimaryopervalid, cx.isminoropervalid
#                           from `case` c join case_extend cx on c.caseId = cx.caseid {}
#                           order by {} limit %s, %s""".format(conditionStr, sort)
#             # left join dim_dept_statis d on c.outDeptId = d.deptid

#             params.append(start)
#             params.append(size)
#             query_data_sql = query_data_sql % tuple(params)
#             self.logger.info("GetDoctorArchivingRateCase, query_data_sql: %s", query_data_sql)
#             query = cursor.execute(query_data_sql)
#             queryset = query.fetchall()
#             self.logger.info("total len is : %s" % totalCount)
#             self.logger.info("queryset len is : %s" % len(queryset))

#         return queryset, totalCount, start

#     def GetDoctorArchivingRateCase(self, request, context):
#         """
#         获取医生归档率详情病历
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorArchivingRateCaseResponse()
#         sizeCount = 0
#         queryset, totalCount, start = self.query_docror_archiving_data(request)
#         if not queryset:
#             return response
#         for item in queryset:
#             sizeCount += 1
#             protoItem = response.items.add()
#             protoItem.id = item[0] if item[0] else ""
#             protoItem.caseId = item[1] if item[1] else ""
#             protoItem.patientId = item[2] if item[2] else ""
#             protoItem.name = item[3] if item[3] else ""
#             protoItem.gender = item[4] if item[4] else ""
#             protoItem.hospital = item[5] if item[5] else ""
#             protoItem.branch = item[6] if item[6] else ""
#             protoItem.department = item[7] if item[7] else ""
#             protoItem.attendDoctor = item[8] if item[8] else ""
#             protoItem.admitTime = item[9].strftime("%Y-%m-%d") if item[9] else ""
#             protoItem.dischargeTime = item[10].strftime("%Y-%m-%d") if item[10] else ""

#             protoItem.inpDays = int(item[12]) if item[12] else 0
#             protoItem.applyFlag = item[13] if item[13] else ""
#             protoItem.applyTime = item[14].strftime("%Y-%m-%d") if item[14] else ""
#             protoItem.applyDoctor = item[15] if item[15] else ""
#             protoItem.reviewFlag = item[16] if item[16] else ""
#             protoItem.reviewer = item[17] if item[17] else ""
#             protoItem.reviewTime = item[18].strftime("%Y-%m-%d") if item[18] else ""
#             if item[19] and item[19] == 1:
#                 protoItem.isDead = '死亡'
#             else:
#                 protoItem.isDead = '未亡'

#             protoItem.isSecondArchiving = item[20] if item[20] else ""
#             protoItem.isThirdArchiving = item[21] if item[21] else ""
#             protoItem.isSeventhArchiving = item[22] if item[22] else ""
#             # 此标记表示没有出院科室问题，使用反了，故此处bool取反
#             protoItem.hasDischargeDeptProblem = False if item[23] else True

#             protoItem.isPrimaryDiagValid = item[24] if item[24] else ""
#             protoItem.isMinorDiagValid = item[25] if item[25] else ""
#             protoItem.isPrimaryOperValid = item[26] if item[26] else ""
#             protoItem.isMinorOperValid = item[27] if item[27] else ""

#             if item[16] == "已退回":
#                 # 只有已退回状态的才显示审核说明
#                 # protoItem.reviewDetail = item[28] if item[28] else ""
#                 protoItem.reviewDetail = ""
#             else:
#                 protoItem.reviewDetail = ""

#         response.total = totalCount
#         response.size = sizeCount
#         response.start = start
#         return response

#     def ExportDoctorArchivingRateCase(self, request, context):
#         """
#         导出医生归档率详情病历
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()
#         queryset, totalCount, start = self.query_docror_archiving_data(request)
#         fileId = uuid.uuid4().hex
#         filename = "%s.xlsx" % fileId
#         fullname = os.path.join(self.privateDataPath, filename)
#         exportName = "医生归档率明细{0}至{1}.xlsx".format(request.startTime, request.endTime)
#         wb = Workbook()
#         patient_id_name = self.context.app.config.get(Config.QC_PATIENT_ID_NAME)
#         titles = [patient_id_name, "姓名", "入院日期", "出院日期", "出院科室", "医生", "住院天数",
#                   "申请标记", "首次申请日期", "首次申请人", "审核标记", "审核日期", "审核人", "审核说明", "是否存在当前出院科室的问题", "死亡标记",
#                   "是否符合2日归档", "是否符合3日归档", "是否符合7日归档"]
#         ws = wb.active
#         ws.append(tuple(titles))
#         for item in queryset:
#             rowData = []
#             rowData.append(item[2] if item[2] else "")
#             rowData.append(item[3] if item[3] else "")
#             rowData.append(item[9].strftime("%Y-%m-%d") if item[9] else "")
#             rowData.append(item[10].strftime("%Y-%m-%d") if item[10] else "")
#             rowData.append(item[7] if item[7] else "")
#             rowData.append(item[8] if item[8] else "")
#             rowData.append(item[12] if item[12] else "0")
#             rowData.append(item[13] if item[13] else "")
#             rowData.append(item[14].strftime("%Y-%m-%d") if item[14] else "")
#             rowData.append(item[15] if item[15] else "")
#             rowData.append(item[16] if item[16] else "")
#             rowData.append(item[18].strftime("%Y-%m-%d") if item[18] else "")
#             rowData.append(item[17] if item[17] else "")

#             hasDischargeDeptProblemFlag = "是" if item[23] else "否"
#             if item[16] == "已退回":
#                 # 只有已退回状态的才显示审核说明
#                 # rowData.append(item[28] if item[28] else "")
#                 rowData.append("")
#                 rowData.append(hasDischargeDeptProblemFlag)
#             else:
#                 rowData.append("")
#                 rowData.append("")

#             deadFlag = "死亡" if item[19] and item[19] == 1 else "未亡"
#             rowData.append(deadFlag)
#             rowData.append(item[20] if item[20] else "")
#             rowData.append(item[21] if item[21] else "")
#             rowData.append(item[22] if item[22] else "")

#             ws.append(tuple(rowData))
#         wb.save(fullname)
#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     def GetMedicalIndicatorStats(self, request, context):
#         """
#         获取病案指标统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetMedicalIndicatorStatsResponse()
#         return response
#         sizeCount = 0
#         start, size = self.getRequestStartAndSize(request)
#         totalCount = 0
#         current = 0
#         removeAllFlag = True
#         # startDate = request.startTime.ToDatetime()
#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         doctor = request.doctor or "全部"
#         args = [request.startTime, request.endTime, branch, department, doctor]
#         if branch == "全部" and department == "全部" and doctor == "全部":
#             removeAllFlag = False

#         sortKey = 14
#         self.logger.info(json.dumps(args, ensure_ascii=False))
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = """call pr_case_medical_index('%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             if queryset:
#                 sortedResult = self.sortMedicalIndicatorResult(queryset, sortKey, request.sortWay, removeAllFlag)
#                 totalCount = len(sortedResult)
#                 self.logger.info("sortedResult len is : %s" % totalCount)
#                 for item in sortedResult:
#                     current += 1
#                     if current <= start:
#                         continue
#                     # 控制分页
#                     if current > start + size:
#                         break
#                     else:
#                         sizeCount += 1
#                         protoItem = response.data.add()
#                         protoItem.branch = item[0] if item[0] else ""
#                         protoItem.department = item[1] if item[1] else ""
#                         protoItem.doctor = item[2] if item[2] else ""
#                         protoItem.admitRecord24HRate = item[3] if item[3] else ""
#                         protoItem.operationRecord24HRate = item[4] if item[4] else ""
#                         protoItem.dischargeRecord24HRate = item[5] if item[5] else ""
#                         protoItem.firstPage24HRate = item[6] if item[6] else ""
#                         protoItem.operationRecordFinishRate = item[7] if item[7] else ""
#                         protoItem.roundRecordFinishRate = item[8] if item[8] else ""
#                         protoItem.rescueRecordFinishRate = item[9] if item[9] else ""
#                         protoItem.secondArchivingRate = item[10] if item[10] else ""
#                         protoItem.archivingFinishRate = item[11] if item[11] else ""
#                         protoItem.unreasonableCaseRate = item[12] if item[12] else ""
#                         protoItem.consentSignedRate = item[13] if item[13] else ""

#         response.total = totalCount
#         response.size = sizeCount
#         response.start = start
#         return response

#     @classmethod
#     def sortMedicalIndicatorResult(cls, queryset, sortKey, sortWay, removeAllFlag):
#         """
#         病案指标结果排序
#         :return:
#         """
#         resultList = []
#         toSortList = list(queryset)
#         if removeAllFlag:
#             # 删除“全部”行
#             toSortList = toSortList[1:]
#         deptDict = defaultdict(list)
#         for item in toSortList:
#             if item[0]:
#                 # branch不为空的行不参与排序
#                 resultList.append(item)
#             else:
#                 deptDict[item[1]].append(item)

#         deptList = list(deptDict.items())
#         if sortWay == "desc":
#             sortedDept = sorted(deptList, key=lambda x: x[1][0][sortKey], reverse=True)
#         else:
#             sortedDept = sorted(deptList, key=lambda x: x[1][0][sortKey])
#         for item in sortedDept:
#             if sortWay == "desc":
#                 sortedRows = sorted(item[1] or "-", key=lambda x: (2 if (x[2] or "-") == "--" else 1, x[2] or "-"), reverse=True)
#             else:
#                 sortedRows = sorted(item[1] or "-", key=lambda x: (0 if (x[2] or "-") == "--" else 1, x[2] or "-"))
#             resultList.extend(sortedRows)

#         return resultList

#     def ExportMedicalIndicatorStats(self, request, context):
#         """
#         导出病案指标统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()
#         removeAllFlag = True
#         # startDate = request.startTime.ToDatetime()
#         branch = request.branch or "全部"
#         department = request.department or "全部"
#         doctor = request.doctor or "全部"
#         args = [request.startTime, request.endTime, branch, department, doctor]
#         if branch == "全部" and department == "全部" and doctor == "全部":
#             removeAllFlag = False
#         sortKey = 14

#         excelTitle = "{0}至{1}病案指标统计".format(request.startTime, request.endTime)
#         exportName = "{0}至{1}病案指标统计.xlsx".format(request.startTime, request.endTime)
#         with self.context.app.mysqlConnection.session() as cursor:
#             fileId = self.getFileId()
#             filename = "%s.xlsx" % fileId
#             fullname = os.path.join(self.privateDataPath, filename)
#             wb = Workbook()
#             call_proc_sql = """call pr_case_medical_index('%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             retCols = query.keys()
#             if queryset:
#                 sortedResult = self.sortMedicalIndicatorResult(queryset, sortKey, request.sortWay, removeAllFlag)
#                 self.generateMedicalIndicatorWorkSheet(sortedResult, wb, retCols, title=excelTitle)
#             wb.save(fullname)
#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     @classmethod
#     def generateMedicalIndicatorWorkSheet(cls, queryset, wb, retCols, title=""):
#         """
#         病案指标统计导出写入excel
#         :return:
#         """
#         ws = wb.active
#         ws.append(tuple(retCols))
#         for row_queryset in queryset:
#             rowData = list(row_queryset[:-1])
#             ws.append(tuple(rowData))

#     def GetMedicalIndicatorStatsCase(self, request, context):
#         """
#         获取病案指标详情接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetMedicalIndicatorStatsCaseResponse()
#         sizeCount = 0
#         queryset, totalCount, start = self.query_medical_indicator_data(request)
#         if not queryset:
#             return response
#         for item in queryset:
#             sizeCount += 1
#             protoItem = response.data.add()
#             # protoItem.id = item[0] if item[0] else ""
#             protoItem.caseId = item[1] if item[1] else ""
#             protoItem.patientId = item[2] if item[2] else ""
#             protoItem.name = item[3] if item[3] else ""
#             protoItem.caseStatus = self.parseCaseStatus(item[12]) if item[12] else ""
#             protoItem.department = item[7] if item[7] else ""
#             protoItem.doctor = item[8] if item[8] else ""
#             protoItem.admitTime = item[9].strftime("%Y-%m-%d") if item[9] else ""
#             protoItem.dischargeTime = item[10].strftime("%Y-%m-%d") if item[10] else ""

#             protoItem.admitRecord24H = item[13] if item[13] else ""
#             protoItem.operationRecord24H = item[14] if item[14] else ""
#             protoItem.dischargeRecord24H = item[15] if item[15] else ""
#             protoItem.firstPage24H = item[16] if item[16] else ""
#             protoItem.operationRecordFinish = item[17] if item[17] else ""
#             protoItem.roundRecordFinish = item[18] if item[18] else ""
#             protoItem.rescueRecordFinish = item[19] if item[19] else ""
#             protoItem.secondArchiving = item[20] if item[20] else ""
#             protoItem.archivingFinish = item[21] if item[21] else ""
#             protoItem.unreasonableCase = item[22] if item[22] else ""
#             protoItem.consentSigned = item[23] if item[23] else ""

#         response.total = totalCount
#         response.size = sizeCount
#         response.start = start
#         return response

#     def query_medical_indicator_data(self, request):
#         """
#         查询病案指标明细数据
#         :return:
#         """
#         start, size = self.getRequestStartAndSize(request)
#         conditionStr = ""
#         params = []
#         # 构造查询条件
#         if request.startTime:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.dischargeTime >= '%s' "
#             params.append(request.startTime)
#         # 出院结束时间
#         if request.endTime:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.dischargeTime <= '%s' "
#             if len(request.endTime) <= 10:
#                 params.append(request.endTime + " 23:59:59")
#             else:
#                 params.append(request.endTime)
#         if request.branch:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.branch = '%s' "
#             params.append(request.branch)
#         if request.department:
#             deptList = request.department.split(",")
#             formatStr = ','.join(['"%s"' % item for item in deptList])
#             conditionStr += (" and " if conditionStr != "" else "") \
#                             + " ifnull(d.statis_name, c.outDeptName) in (%s)" % formatStr
#         if request.doctor and request.doctor != "--":
#             doctorList = request.doctor.split(",")
#             doctorListStr = ",".join(['%s'] * len(doctorList))
#             conditionStr += (" and " if conditionStr != "" else "") + " c.attendDoctor in (%s) " % doctorListStr
#         if request.status:
#             conditionStr += (" and " if conditionStr != "" else "") + " c.status = '%s' "
#             params.append(request.status)

#         if conditionStr:
#             conditionStr = " where " + conditionStr

#         # 排序规则
#         if request.sortKey:
#             if request.sortKey not in ["dischargeTime", "admitTime"]:
#                 self.logger.error("sortKey is not support.")
#                 return None, None, None
#         if request.sortWay:
#             if request.sortWay.lower() not in ["asc", "desc", "null"]:
#                 self.logger.error("sortWay is not support.")
#                 return None, None, None
#         sort = (request.sortKey if request.sortKey else "dischargeTime") + " " + (
#             request.sortWay if request.sortWay and request.sortWay != "null" else "ASC")

#         # get case list
#         with self.context.app.mysqlConnection.session() as cursor:
#             # get total count
#             query_count_sql = """select count(id) from `case` as c join case_extend cx on c.caseId = cx.caseid 
#                         left join dim_dept_statis d on c.outDeptId = d.deptid """ + (
#                 conditionStr if conditionStr else "")
#             query_count_sql = query_count_sql % tuple(params)
#             self.logger.info("GetMedicalIndicatorStatsCase, query_count_sql: %s", query_count_sql)
#             query = cursor.execute(query_count_sql)
#             ret = query.fetchone()
#             totalCount = ret[0]

#             query_data_sql = """select id, c.caseId,c.patientId, c.name, c.gender, c.hospital, c.branch,
#                               c.outDeptName, c.attendDoctor, c.admitTime,c.dischargeTime,cx.outdeptname, 
#                               c.status,cx.inrecord24hcomplete, cx.opsrecord24hcomplete, cx.outrecord24hcomplete, 
#                               cx.firstpage24hcomplete, cx.opsrecordwhole, cx.doctorroundswhole, 
#                               cx.rescuerecord6hcomplete, cx.isSecondArchiving,
#                               (case when cx.auditflag='已退回' then '否' else '是' end ) ,cx.isemrcopy ,cx.isnormmrc 
#                               from `case` c join case_extend cx on c.caseId = cx.caseid 
#                               left join dim_dept_statis d on c.outDeptId = d.deptid {} 
#                               order by {} limit %s, %s""".format(conditionStr, sort)
#             params.append(start)
#             params.append(size)
#             query_data_sql = query_data_sql % tuple(params)
#             self.logger.info("GetMedicalIndicatorStatsCase, query_data_sql: %s", query_data_sql)
#             query = cursor.execute(query_data_sql)
#             queryset = query.fetchall()
#             self.logger.info("total len is : %s" % totalCount)
#             self.logger.info("queryset len is : %s" % len(queryset))

#         return queryset, totalCount, start

#     @classmethod
#     def parseCaseStatus(cls, status, refused=False):
#         """
#         parse case status
#         :return:
#         """
#         if status == 0:
#             return "未申请"
#         elif status == 1:
#             if not refused:
#                 return "待审核"
#             else:
#                 return "重新申请"
#         elif status == 3:
#             return "已审核"
#         elif status == 4:
#             return "已退回"
#         elif status == 5:
#             return "未申请"
#         return ""

#     def ExportMedicalIndicatorStatsCase(self, request, context):
#         """
#         导出医生归档率详情病历
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()

#         queryset, totalCount, start = self.query_medical_indicator_data(request)
#         fileId = uuid.uuid4().hex
#         filename = "%s.xlsx" % fileId
#         fullname = os.path.join(self.privateDataPath, filename)
#         exportName = "{0}至{1}指标统计明细.xlsx".format(request.startTime, request.endTime)
#         wb = Workbook()
#         patient_id_name = self.context.app.config.get(Config.QC_PATIENT_ID_NAME)
#         titles = [patient_id_name, "姓名", "入院日期", "出院日期", "病历状态", "科室", "医生", "入院记录24小时完成",
#                   "手术记录24小时完成", "出院记录24小时完成", "病案首页24小时完成", "手术相关记录完整",
#                   "医生查房记录完整", "患者抢救记录及时完成", "出院患者病历2日归档", "出院患者病历归档完整",
#                   "不合理复制病历发生", "知情同意书规范签署"]
#         ws = wb.active
#         ws.append(tuple(titles))

#         totalCount = len(queryset)
#         self.logger.info("queryset len is : %s" % totalCount)
#         if queryset:
#             for item in queryset:
#                 rowData = []
#                 rowData.append(item[2] if item[2] else "")
#                 rowData.append(item[3] if item[3] else "")
#                 rowData.append(item[9].strftime("%Y-%m-%d") if item[9] else "")
#                 rowData.append(item[10].strftime("%Y-%m-%d") if item[10] else "")
#                 caseStatus = self.parseCaseStatus(item[12]) if item[12] else ""
#                 rowData.append(caseStatus)
#                 rowData.append(item[7] if item[7] else "")
#                 rowData.append(item[8] if item[8] else "")

#                 for idx in range(13, 24):
#                     rowData.append(item[idx] if item[idx] else "")

#                 ws.append(tuple(rowData))
#         wb.save(fullname)
#         response.id = str(fileId)
#         response.fileName = exportName
#         return response

#     def GetFirstPageProblems(self, request, context):
#         """ 病案首页问题统计
#         """
#         response = GetFirstPageProblemsResponse()
#         start, size = self.getRequestPageAndCount(request)
#         sortKey = {
#             "totalCount": "firstProblemCount",
#             "requiredCount": "requiredProblemCount",
#             "optionalCount": "optionalProblemCount"
#         }
#         if not request.sortKey:
#             request.sortKey = "totalCount"
#         with self.context.app.mysqlConnection.session() as cursor:
#             query_sql = '''select c.caseId, c.patientId, c.name, c.outDeptName, c.wardName, c.attendDoctor, c.admitTime, 
#             c.dischargeTime, c.status, ar.firstProblemCount, ar.requiredProblemCount, ar.optionalProblemCount 
#             from `case` c left outer join audit_record ar on c.audit_id = ar.id 
#             left outer join dim_dept_statis dds on dds.deptid = c.outDeptId '''
#             query_count_sql = '''select count(*) from `case` c left outer join audit_record ar on c.audit_id = ar.id 
#             left outer join dim_dept_statis dds on dds.deptid = c.outDeptId '''
#             filter_sql = "where 1 = 1"
#             if request.startTime:
#                 filter_sql += " and c.dischargeTime >= '%s'" % request.startTime
#             if request.endTime:
#                 filter_sql += " and c.dischargeTime <= '%s 23:59:59'" % request.endTime
#             if request.outDept:
#                 filter_sql += " and dds.statis_name = '%s'" % request.outDept
#             if request.status:
#                 filter_sql += " and c.status = '%s'" % request.status
#             if request.problemFlag:
#                 if request.problemFlag == 1:
#                     filter_sql += " and ar.firstProblemCount > 0"
#                 elif request.problemFlag == 2:
#                     filter_sql += " and ar.firstProblemCount = 0"
#             if request.input:
#                 filter_sql += """ and c.patientId like '%{name}%' or c.name like '%{name}%' 
#                 or c.attendDoctor like '%{name}%'""".format(name=request.input)
#             order_by_sql = ""
#             if request.sortKey:
#                 if not request.sortWay or request.sortWay.lower() not in ["asc", "desc"]:
#                     request.sortWay = "DESC"
#                 if request.sortKey in ["patientId", "dischargeTime"]:
#                     order_by_sql += " order by c.%s %s" % (request.sortKey, request.sortWay)
#                 elif sortKey.get(request.sortKey):
#                     order_by_sql += " order by ar.%s %s" % (sortKey.get(request.sortKey), request.sortWay)

#             query_sql += filter_sql
#             query_count_sql += filter_sql
#             query_sql += order_by_sql
#             query_sql += " limit %s, %s" % (start, size)
#             query_count = cursor.execute(query_count_sql)
#             print("GetFirstPageProblems, query_sql:", query_sql)
#             print("GetFirstPageProblems, query_count_sql:", query_count_sql)
#             response.total = query_count.fetchone()[0]
#             print("response.total:", response.total)
#             query = cursor.execute(query_sql)
#             data = query.fetchall()

#             for item in data:
#                 protoItem = response.data.add()
#                 protoItem.caseId = item[0] or ""
#                 protoItem.patientId = item[1] or ""
#                 protoItem.name = item[2] or ""
#                 protoItem.outDept = item[3] or ""
#                 protoItem.ward = item[4] or ""
#                 protoItem.attend = item[5] or ""
#                 protoItem.admitTime = item[6].strftime("%Y-%m-%d") if item[6] else ""
#                 protoItem.dischargeTime = item[7].strftime("%Y-%m-%d") if item[7] else ""
#                 protoItem.status = item[8] or 0
#                 protoItem.totalCount = item[9] or 0
#                 protoItem.requiredCount = item[10] or 0
#                 protoItem.optionalCount = item[11] or 0
#         return response

#     @classmethod
#     def getRequestPageAndCount(cls, request):
#         """
#         获取分页请求中的start和size
#         :param request:
#         :return:
#         """
#         size = 1000
#         start = 0
#         MAXSIZE = 1000
#         if request.count and 0 < request.count <= MAXSIZE:
#             size = request.count
#         if request.count > MAXSIZE:
#             size = MAXSIZE

#         if request.page:
#             start = (request.page - 1) * request.count
#         return start, size

#     def GetFirstPageScoreStats(self, request, context):
#         """
#         各科室首页分数统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetFirstPageScoreStatsResponse()

#         args = ["各科室首页分数统计", request.startTime, request.endTime, ""]
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = '''call pr_case_firstpagescore("%s", "%s", "%s", "%s")''' % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("GetFirstPageScoreStats, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             if queryset:
#                 self.logger.info("GetFirstPageScoreStats len queryset: %s", len(queryset))
#                 for item in queryset:
#                     protoItem = response.data.add()
#                     protoItem.department = item[0] if item[0] else ""
#                     protoItem.maxScore = float(item[1]) if item[1] else 0
#                     protoItem.minScore = float(item[2]) if item[2] else 0
#                     protoItem.avgScore = float(item[3]) if item[3] else 0
#                     protoItem.hospitalAvgScore = float(item[4]) if item[4] else 0

#         return response

#     def GetFirstPageScoreDistribution(self, request, context):
#         """
#         首页分数分布统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetFirstPageScoreDistributionResponse()

#         args = ["首页分数分布", request.startTime, request.endTime, ""]
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = '''call pr_case_firstpagescore("%s", "%s", "%s", "%s")''' % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("GetFirstPageScoreDistribution, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             if queryset:
#                 self.logger.info("GetFirstPageScoreDistribution len queryset: %s", len(queryset))
#                 for item in queryset:
#                     protoItem = response.data.add()
#                     protoItem.area = item[1] if item[1] else ""
#                     protoItem.caseCount = int(item[0]) if item[0] else 0
#                     protoItem.areaIndex = int(item[2]) if item[2] else 0

#         return response

#     def GetFirstPageIndicateStats(self, request, context):
#         """
#         首页通用指标统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonStatsResponse()
#         if not request.indicateName:
#             self.logger.error("GetFirstPageIndicateStats: param indicateName is required.")
#             context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
#             context.set_details("GetFirstPageIndicateStats: param indicateName is required.")
#             return response

#         limitSize = request.count if request.count else 10
#         params = request.indicateParams if request.indicateParams else ""
#         args = [request.indicateName, request.startTime, request.endTime, params]
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = '''call pr_case_firstpagescore("%s", "%s", "%s", "%s")''' % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("GetFirstPageIndicateStats, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             if queryset:
#                 self.logger.info("GetFirstPageIndicateStats len queryset: %s", len(queryset))
#                 size = 0
#                 for item in queryset:
#                     size += 1
#                     if size > limitSize:
#                         break
#                     protoItem = response.items.add()
#                     protoItem.name = item[0] if item[0] else ""
#                     protoItem.count = int(item[1]) if item[1] else 0

#         return response

#     def GetFirstPageProblemConfig(self, request, context):
#         """
#         获取首页问题配置接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetFirstPageProblemConfigResponse()

#         with self.context.app.mysqlConnection.session() as cursor:
#             query_sql = "select distinct name ,status, sort from dim_firstpagescore where is_select = 1 order by sort;"
#             query = cursor.execute(query_sql)
#             self.logger.info("GetFirstPageProblemConfig, query_sql: %s", query_sql)
#             ret = query.fetchall()
#             for x in ret:
#                 protoItem = response.data.add()
#                 protoItem.name = x[0] if x[0] else ""
#                 protoItem.status = int(x[1]) if x[1] else 0
#                 protoItem.sortIndex = int(x[2]) if x[2] else 0

#         return response

#     def ModifyFirstPageProblemConfig(self, request, context):
#         """
#         修改首页问题排序接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonBatchResponse()
#         if request.data:
#             with self.context.app.mysqlConnection.session() as cursor:
#                 for item in request.data:
#                     updateSql = "update dim_firstpagescore set status = {}, sort = {} where name = '{}';".format(
#                         item.status, item.sortIndex, item.name)
#                     self.logger.info(updateSql)
#                     cursor.execute(updateSql)
#                 response.isSuccess = True

#         return response

#     def GetBatchFirstPageIndicateStats(self, request, context):
#         """
#         首页通用指标统计接口
#         :param request:
#         :param context:
#         :return:
#         """
#         response = BatchCommonStatsResponse()
#         if not request.indicates:
#             return response

#         resultDict = {}
#         plist = []
#         start = time.time()
#         indicatorList = []
#         self.logger.error("GetBatchFirstPageIndicateStats, start time: %s, len: %s", start, len(request.indicates))
#         for item in request.indicates:
#             params = item.params if item.params else ""
#             indicatorID = "%s-%s" % (item.name, params)
#             indicatorList.append(indicatorID)
#             p = threading.Thread(target=self.processStats,
#                                  args=(indicatorID, item, request.startTime, request.endTime, resultDict))
#             p.start()
#             plist.append(p)

#         for x in plist:
#             x.join(90)
#             # x.close()

#         self.logger.error("GetBatchFirstPageIndicateStats end time: %s, use time: %s", time.time(), time.time() - start)
#         # get the result data
#         for key in indicatorList:
#             result = resultDict[key]
#             protoItem = response.items.add()
#             keyArr = key.split("-")
#             protoItem.name = keyArr[0]
#             if len(keyArr) == 2 and keyArr[1]:
#                 protoItem.params = keyArr[1]
#             for retItem in result:
#                 protoItemVal = protoItem.items.add()
#                 protoItemVal.name = retItem.get("dept") if retItem.get("dept") else ""
#                 protoItemVal.count = retItem.get("count") if retItem.get("count") else 0

#         return response

#     def processStats(self, indicatorID, indicatorItem, startTime, endTime, resultDict):
#         """
#         process Stats
#         # 并行处理单元
#         :return:
#         """
#         result = self.mysqlStats(indicatorItem, startTime, endTime)
#         resultDict[indicatorID] = result

#     def mysqlStats(self, indicatorItem, startTime, endTime):
#         """
#         mysql Stats
#         :return:
#         """
#         result = []
#         limitSize = indicatorItem.count if indicatorItem.count else 10
#         params = indicatorItem.params if indicatorItem.params else ""
#         args = [indicatorItem.name, startTime, endTime, params]
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = '''call pr_case_firstpagescore("%s", "%s", "%s", "%s")''' % tuple(args)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("mysqlStats, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()

#             if queryset:
#                 size = 0
#                 self.logger.info("mysqlStats, queryset len is : %s" % len(queryset))
#                 for item in queryset:
#                     size += 1
#                     if size > limitSize:
#                         break
#                     temp = {
#                         "dept": item[0] if item[0] else "",
#                         "count": int(item[1]) if item[1] else 0
#                     }
#                     result.append(temp)
#         return result

#     def GetStatsDataUpdateStatus(self, request, context):
#         """
#         获取统计数据更新状态信息(首页评分,归档率等统计)
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsDataUpdateStatusResponse()

#         result = self.getStatsUpdateState()
#         response.status = result.get("status") if result.get("status") else 0
#         updateDatetime = result.get("updatetime") + timedelta(hours=8)
#         self.logger.info(updateDatetime)
#         response.lastUpdateTime = updateDatetime.strftime('%Y-%m-%d %H:%M:%S') if result.get("updatetime") else None
#         return response

#     def getStatsUpdateState(self, is_expert=0):
#         """
#         查询统计数据更新状态
#         :param is_expert:
#         :return:
#         """
#         result = {}
#         with self.context.app.mysqlConnection.session() as cursor:
#             table = "case_updatestatus" if not is_expert else "case_updatestatus_expert"
#             query_sql = "select updatetime, updatestatus from %s" % table
#             query = cursor.execute(query_sql)
#             ret = query.fetchone()
#             if ret:
#                 self.logger.info(ret)
#                 result["updatetime"] = ret[0] if ret[0] else ""
#                 result["status"] = int(ret[1]) if ret[1] else 0

#         return result

#     def StatsDataUpdate(self, request, context):
#         """
#         更新统计数据接口(首页评分,归档率等统计)
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsDataUpdateResponse()

#         result = self.getStatsUpdateState()
#         if result.get("status") == 1 or result.get("updatetime") > (datetime.now() - timedelta(minutes=5)):
#             response.isSuccess = False
#             response.message = "数据更新频率太高"
#             return response

#         with self.context.app.mysqlConnection.session() as cursor:
#             update_sql = "update case_updatestatus set updatestatus = 1, updatetime = Now();"
#             ret = cursor.execute(update_sql)
#             if ret:
#                 self.logger.info(ret)
#                 response.isSuccess = True
#                 self.logger.info("start finishDataUpdate time is : %s " % time.time())
#                 p = Process(target=self.finishDataUpdate, args=(cursor, ))
#                 p.daemon = True
#                 p.start()
#                 self.logger.info("finishDataUpdate time is : %s " % time.time())
#         return response

#     def finishDataUpdate(self, cursor):
#         time.sleep(5)
#         call_proc_sql = '''call pr_case_archiverate_process("", "")'''
#         query = cursor.execute(call_proc_sql)
#         # procRet = query.fetchall()
#         # self.logger.info("finishDataUpdate call proc ret is: %s" % procRet)
#         finishSql = "update case_updatestatus set updatestatus = 2;"
#         ret = cursor.execute(finishSql)
#         if ret:
#             self.logger.info("finishDataUpdate: ret is : %s" % ret)
#         self.logger.info("finishDataUpdate inside time is : %s " % time.time())

#     def GetProblemCategoryStats(self, request, context):
#         """质控问题按照类别统计
#         """
#         response = GetProblemCategoryStatsResponse()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         if not request.auditType:
#             return response
#         params = ["branch", "ward", "department", "attending", "startTime", "endTime", "emrName",
#                   "category", "problem", "auditType", "caseType", "problemType", "fixed", "start", "size"]
#         req = {c: getattr(request, c) for c in params}
#         req['withTotal'] = True

#         field, pList = app.getDeptPermission(request.operatorId)
#         req['pField'] = field
#         req['pList'] = pList
#         logging.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')
#         if request.itemsId:
#             req['qcItemsId'] = [0]
#             for item in request.itemsId.split(','):
#                 try:
#                     req['qcItemsId'].append(int(item))
#                 except Exception as e:
#                     logging.info(e)
#         req['itemType'] = request.itemtype

#         req = GetProblemStatsRequest(**req)
#         results, total = app.getProblemStats(req)
#         response.total = total

#         qcitems = app.getQcItems()
#         for stats in results:
#             qcItemId = stats.get('qcItemId')
#             counting = stats.get('counting')
#             for item in qcitems:
#                 if item.id == qcItemId:
#                     protoItem = response.data.add()
#                     protoItem.id = qcItemId
#                     protoItem.instruction = item.requirement or ''
#                     protoItem.emrName = item.standard_emr if item.standard_emr and item.standard_emr != '0' else '缺失文书'
#                     protoItem.category = QCITEM_CATEGORY.get(item.category, "")
#                     protoItem.count = counting
#                     break
#         return response

#     def GetCaseByProblem(self, request, context):
#         """查询存在某个质控问题的病历列表
#         """
#         response = GetCaseByProblemResponse()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         params = ["branch", "ward", "department", "attending", "startTime", "endTime",
#                   "auditType", "caseType", "problemType", "fixed", "start", "size"]
#         req = {c: getattr(request, c) for c in params}
#         req['qcItemsId'] = [request.itemId]
#         req['withTotal'] = True

#         field, pList = app.getDeptPermission(request.operatorId)
#         req['pField'] = field
#         req['pList'] = pList
#         logging.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')

#         req = GetProblemStatsRequest(**req)

#         results, total, case_pstatus, problem_data = app.getProblemStatsCase(req)
#         response.total = total
#         pstatus = {item.get('caseId'): item.get('pstatus') for item in case_pstatus}
#         for item in results:
#             protoItem = response.data.add()
#             protoItem.id = item.id
#             protoItem.caseId = item.caseId or ""
#             protoItem.patientId = item.inpNo or item.patientId or ""
#             protoItem.visitTimes = item.visitTimes or 0
#             protoItem.name = item.name or ""
#             protoItem.age = str(item.age or 0) + str(item.ageUnit or "")
#             protoItem.gender = item.gender or ""
#             protoItem.branch = item.branch or ""
#             protoItem.department = item.department or ""
#             protoItem.dischargeDept = item.outDeptName or ""
#             protoItem.attendDoctor = item.attendDoctor or ""
#             protoItem.admitTime = item.admitTime.strftime('%Y-%m-%d') if item.admitTime else ""
#             protoItem.dischargeTime = item.dischargeTime.strftime('%Y-%m-%d') if item.dischargeTime else ""
#             protoItem.status = item.status or 0
#             protoItem.statusName = parseCaseStatus(protoItem.status)
#             protoItem.ward = item.wardName or ""
#             if item.TagsModel:
#                 for tag in item.TagsModel:
#                     tagItem = protoItem.caseTags.add()
#                     tagItem.name = tag.name or ""
#                     tagItem.code = tag.code
#                     tagItem.icon = tag.icon or ""
#             protoItem.fixed = pstatus.get(item.caseId)
#             problem_info = problem_data.get(item.caseId, {})
#             protoItem.fromAi = AI_DICT.get(problem_info.get("from_ai") or 0, "未知")
#             protoItem.createUser = problem_info.get("create_doctor") or ""
#             protoItem.createTime = problem_info.get("create_time") or ""
#             protoItem.solveUser = problem_info.get("fix_doctor") or ""
#             protoItem.solveTime = problem_info.get("fix_time") or ""
#         return response

#     def ExportProblemCateStats(self, request, context):
#         """质控问题统计导出
#         """
#         response = FileData()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         params = ["branch", "ward", "department", "attending", "startTime", "endTime", "emrName",
#                   "category", "problem", "auditType", "caseType", "problemType", "fixed"]
#         req = {c: getattr(request, c) for c in params}
#         req['size'] = 1000

#         field, pList = app.getDeptPermission(request.operatorId)
#         req['pField'] = field
#         req['pList'] = pList
#         logging.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')

#         req = GetProblemStatsRequest(**req)
#         results, tmp = app.getProblemStats(req)

#         data = []
#         qcitems = app.getQcItems()
#         print(f'一共[{len(results)}]个质控问题')
#         for stats in results:
#             qcItemId = stats.get('qcItemId')
#             counting = stats.get('counting')
#             for item in qcitems:
#                 if item.id == qcItemId:
#                     req = {c: getattr(request, c) for c in params}
#                     req['qcItemsId'] = [qcItemId]
#                     req['size'] = 1000
#                     req['pField'] = field
#                     req['pList'] = pList
#                     req = GetProblemStatsRequest(**req)
#                     print(f'查询[{item.requirement}]相关病历列表')
#                     case_list, total, case_pstatus, _ = app.getProblemStatsCase(req)
#                     pstatus = {item.get('caseId'): item.get('pstatus') for item in case_pstatus}
#                     for c in case_list:
#                         data.append((qcItemId, item.requirement, counting, c.caseId, c.inpNo or c.patientId, c.name, c.department, c.outDeptName, c.admitTime, c.dischargeTime, c.attendDoctor, c.status, pstatus.get(c.caseId, "")))
#                     break
#         # 排序
#         colsTitle = []
#         results = []
#         patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME)
#         if request.exportType == 1:
#             colsTitle = ["问题描述", patient_id_name, "姓名", "入院科室", "出院科室", "入院日期", "出院日期", "医生", "病历状态", "问题状态"]
#             for item in data:
#                 results.append((item[1], item[4], item[5], item[6], item[7], item[8], item[9], item[10], parseCaseStatus(item[11]), item[12]))
#         if request.exportType == 2:
#             data.sort(key=lambda x: (x[3], x[0]))
#             colsTitle = [patient_id_name, "姓名", "入院科室", "出院科室", "入院日期", "出院日期", "医生", "病历状态", "问题描述", "问题状态"]
#             for item in data:
#                 results.append((item[4], item[5], item[6], item[7], item[8], item[9], item[10], parseCaseStatus(item[11]), item[1], item[12]))
#         # 保存文件
#         wb = Workbook()
#         ws = wb.active
#         ws.append(tuple(colsTitle))
#         bold_font = Font(bold=True)
#         for cell in ws["1:1"]:
#             cell.font = bold_font
#         for row_queryset in results:
#             ws.append(row_queryset)
#         fileId = uuid.uuid4().hex
#         wb.save(os.path.join(self.privateDataPath, str(fileId) + ".xlsx"))

#         response.id = fileId
#         auditTypeDict = {
#             'active': "事中质控",
#             'final': "事后质控",
#             'department': "科室质控",
#             'hospital': "病案质控",
#             'firstpage': "编码质控",
#             'expert': "专家质控"
#         }
#         response.fileName = datetime.now().strftime('%Y-%m-%d') + "_" + "质控问题统计_" + auditTypeDict.get(request.auditType, '') + ".xlsx"
#         return response

#     def ExportProblemCateStats1(self, request, context):
#         """院级病历得分病历列表导出
#         """
#         response = FileData()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         params = ["branch", "ward", "department", "attending", "startTime", "endTime", "emrName",
#                   "category", "problem", "auditType", "caseType", "problemType"]
#         req_dict = {c: getattr(request, c) for c in params}
#         req_dict['size'] = 1000
#         req = GetProblemStatsRequest(**req_dict)
#         results, _ = app.getProblemStats(req)
#         data = []
#         qc_items = app.getQcItems()
#         qc_item_requirement_dict = {item.id: item.requirement for item in qc_items}

#         qc_item_id_list = [stats.get('qcItemId') for stats in results]
#         case_id_qc_item_id_dict = {stats.get('caseId'): stats.get('qcItemId') for stats in results}
#         req_dict['qcItemsId'] = qc_item_id_list

#         new_req = GetProblemStatsRequest(**req_dict)
#         results, total, _, _ = app.getProblemStatsCase(new_req)

#         for c in results:
#             caseId = c.caseId
#             qcItemId = case_id_qc_item_id_dict.get(caseId, "")
#             requirement = qc_item_requirement_dict.get(qcItemId, "")
#             data.append((qcItemId, requirement, 0, c.caseId, c.patientId, c.name, c.department,
#                          c.outDeptName, c.admitTime, c.dischargeTime, c.attendDoctor, c.status))

#         colsTitle = []
#         results = []
#         patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME)
#         if request.exportType == 1:
#             colsTitle = ["问题描述", patient_id_name, "姓名", "入院科室", "出院科室", "入院日期", "出院日期", "医生", "病历状态"]
#             for item in data:
#                 results.append((item[1], item[4], item[5], item[6], item[7], item[8], item[9], item[10],
#                                 parseCaseStatus(item[11])))
#         elif request.exportType == 2:
#             data.sort(key=lambda x: (x[3], x[0]))
#             colsTitle = [patient_id_name, "姓名", "入院科室", "出院科室", "入院日期", "出院日期", "医生", "病历状态", "问题描述"]
#             for item in data:
#                 results.append((item[4], item[5], item[6], item[7], item[8], item[9], item[10],
#                                 parseCaseStatus(item[11]), item[1]))

#         df = pd.DataFrame(results, columns=colsTitle)
#         auditTypeDict = {
#             'active': "事中质控",
#             'final': "事后质控",
#             'department': "科室质控",
#             'hospital': "病案质控",
#             'firstpage': "编码质控",
#             'expert': "专家质控"
#         }
#         file_name = datetime.now().strftime('%Y-%m-%d') + "_" + "质控问题统计_" + auditTypeDict.get(request.auditType, '') + ".xlsx"
#         file_id = uuid.uuid4().hex
#         path_file_name = os.path.join(self.privateDataPath, str(file_id) + ".xlsx")
#         df.to_excel(path_file_name, index=False)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     @classmethod
#     def keep_one(cls, num, ratio=False):
#         """
#         保留一位小数
#         :param num:
#         :param ratio: 是否带单位符号
#         :return:
#         """
#         if not num:
#             num = 0
#         minus = False
#         if num < 0:
#             num = float(str(num)[1:])
#             minus = True
#         symbol = '%'
#         if num > 100:
#             x = '%.1f' % num
#         elif num >= 1:
#             x = '%0.3g' % num  # '1.xx or 11.x'
#         elif num >= 0.1:
#             x = '%0.2f' % num  # 0.xx
#         elif num >= 0.01:
#             if ratio:
#                 n = num * 10
#                 x, symbol = '%0.2f' % n, '‰'  # 0.xx
#             else:
#                 x = '%.1f' % num
#         elif num > 0.0001:
#             if ratio:
#                 n = num * 100
#                 x, symbol = '%0.2f' % n, '‱'
#             else:
#                 x = '%.1f' % num
#         else:
#             x = '0'
#         if minus and x != '0':
#             x = "-" + x
#         if ratio:
#             return x + symbol
#         return x

#     @classmethod
#     def get_file_id(cls, file_name):
#         """
#         获取文件id
#         :return:
#         """
#         return uuid.uuid3(uuid.NAMESPACE_DNS, file_name + str(random.randint(100, 1000))).hex

#     @classmethod
#     def format_header_data(cls, response, header, data, is_sort=0, not_sort_header=None, first_title_dict={}):
#         """
#         序列化标题+数据
#         """
#         if not_sort_header is None:
#             not_sort_header = []
#         for item in header:
#             if item.name in ["sort_time"]:
#                 continue
#             protoHeader = response.headers.add()
#             protoHeader.title = item.name if not hasattr(item, "displayName") else item.displayName
#             protoHeader.key = item.name
#             if "-" in item.name:
#                 protoHeader.firstTitle = item.name.split("-")[0]
#             if first_title_dict:
#                 protoHeader.firstTitle = first_title_dict.get(item.name, "")
#             if item.name not in not_sort_header and is_sort:
#                 protoHeader.isSort = is_sort
#         for row_data in data:
#             if StatsRepository.verify_row_data(row_data):
#                 protoData = response.data.add()
#                 for key, value in row_data.items():
#                     protoData.item[key] = str(value)

#     def format_dept_score_pic_data(self, result, response, level):
#         """
#         格式化科室成绩图数据
#         :return:
#         """
#         ward_field = "病区"
#         if self.context.app.config.get(Config.QC_ASSIGN_DIMENSION) == 1:
#             ward_field = "科室"
#         first_name = ""
#         second_name = ""
#         for item in result:
#             if item.get(ward_field, "") and item.get(ward_field, "") == "总计":
#                 if not first_name:
#                     first_name = item.get("内外科", "")
#                 else:
#                     second_name = item.get("内外科", "")
#         proto_data1 = response.data.add()
#         proto_data1.dataName = first_name
#         proto_data2 = response.data.add()
#         proto_data2.dataName = second_name
#         level = level if level == "平均分" else level + "率"
#         is_total = 0
#         for item in result:
#             if item.get(ward_field, "") == "总计":
#                 is_total += 1
#             if is_total == 1:
#                 if item.get(ward_field, "") and item.get(ward_field, "") != "总计":
#                     proto_detail_data = proto_data1.items.add()
#                     proto_detail_data.xData = item.get(ward_field, "")
#                     num = item[level] if level == "平均分" else item[level][:-1]
#                     proto_detail_data.yData = num
#             elif is_total == 2:
#                 if item.get(ward_field, "") and item.get(ward_field, "") != "总计":
#                     proto_detail_data = proto_data2.items.add()
#                     proto_detail_data.xData = item.get(ward_field, "")
#                     num = item[level] if level == "平均分" else item[level][:-1]
#                     proto_detail_data.yData = num

#     def get_dept_level_data(self, result, response):
#         """
#         内外科成绩概览 级别数量图数据
#         :return:
#         """
#         ward_field = "病区"
#         if self.context.app.config.get(Config.QC_ASSIGN_DIMENSION) == 1:
#             ward_field = "科室"
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         for item in result:
#             if item.get(ward_field, "") and item.get(ward_field, "") == "总计":
#                 proto_data = response.items.add()
#                 proto_data.deptType = item.get("内外科", "")
#                 proto_data.data.total = item.get("总数", 0)
#                 char_data = proto_data.data.data.add()
#                 for level in qc_stats_level:
#                     key = level + "数"
#                     char_data.xData = key
#                     char_data.yData = item.get(key, 0)

#     def get_common_stats_pic_response(self, call_proc_sql, response, request, level=2, is_rate=0):
#         """
#         专家统计通用获取 折线/柱状图数据
#         :return:
#         """
#         endTime = request.endTime
#         startTime = StatsRepository.get_start_time(endTime)
#         endTime = StatsRepository.get_end_time(endTime)
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("get_common_stats_pic_response, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             res_dict = {}
#             if queryset:
#                 for item in queryset:
#                     if item[0] not in res_dict:
#                         res_dict[item[0]] = StatsRepository.get_init_dict(startTime, endTime)
#                     data = item[level]
#                     if is_rate and level != 3:
#                         data = item[level] / item[2] * 100
#                     res_dict[item[0]][item[1]] = data
#                 for branch in res_dict:
#                     if not branch:
#                         continue
#                     protoItem = response.data.add()
#                     protoItem.dataName = branch
#                     detail_data = res_dict[branch]
#                     for x, y in detail_data.items():
#                         detailData = protoItem.items.add()
#                         detailData.xData = str(x)
#                         detailData.yData = self.keep_one(y)

#     def get_common_header_data(self, target_name, request):
#         """
#         专家统计 通用获取标题+数据列表数据+配置
#         :return:
#         """
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         ward_field = "病区"
#         if self.context.app.config.get(Config.QC_ASSIGN_DIMENSION) == 1:
#             ward_field = "科室"
#         qc_stats_level = qc_stats_level.split(",")
#         total = 0
#         with self.context.app.mysqlConnection.session() as cursor:
#             data = []
#             if target_name == "质控情况分布":
#                 call_proc_sql = self.get_call_proc_sql(target_name, request)
#                 query = cursor.execute(call_proc_sql)
#                 self.logger.info("get_common_stats_pic_response, call_proc_sql: %s", call_proc_sql)
#                 queryset = query.fetchall()
#                 data_yaml = EXPERT_ALL_SCORE_YAML.format(first=qc_stats_level[0], second=qc_stats_level[1],
#                                                          third=qc_stats_level[2])
#                 for item in queryset:
#                     tmp = {"院区": item[0] or "", "平均分": self.keep_one(item[2]), "总数": item[1] or 0,
#                            "{}率".format(qc_stats_level[0]): self.keep_one(item[6], True),
#                            "{}率".format(qc_stats_level[1]): self.keep_one(item[7], True),
#                            "{}率".format(qc_stats_level[2]): self.keep_one(item[8], True),
#                            "{}数".format(qc_stats_level[0]): item[3], "{}数".format(qc_stats_level[1]): item[4],
#                            "{}数".format(qc_stats_level[2]): item[5]}
#                     data.append(tmp)
#                 total = len(data)
#             elif target_name == "科室成绩概览":
#                 call_proc_sql = self.get_call_proc_sql(target_name, request)
#                 query = cursor.execute(call_proc_sql)
#                 self.logger.info("get_common_stats_pic_response, call_proc_sql: %s", call_proc_sql)
#                 queryset = query.fetchall()
#                 data_yaml = INTERNAL_SURGERY_LIST_YAML.replace("[first]", qc_stats_level[0]).replace(
#                     "[second]", qc_stats_level[1]).replace("[third]", qc_stats_level[2]).replace("[ward]", ward_field)
#                 for item in queryset:
#                     if not item[0]:
#                         continue
#                     tmp = {"内外科": item[0], ward_field: item[1], "总数": int(item[2]), "总分": float(item[3]),
#                            "{}数".format(qc_stats_level[0]): int(item[4]), "{}数".format(qc_stats_level[1]): int(item[5]),
#                            "{}数".format(qc_stats_level[2]): int(item[6])}
#                     data.append(tmp)
#                 total = len(data)
#             elif target_name == "医生成绩统计":
#                 call_proc_sql = self.get_call_proc_sql(target_name, request)
#                 query = cursor.execute(call_proc_sql)
#                 self.logger.info("get_common_stats_pic_response, call_proc_sql: %s", call_proc_sql)
#                 queryset = query.fetchall()
#                 data_yaml = DOCTOR_SCORE_LIST_YAML.replace("[first]", qc_stats_level[0]).replace(
#                     "[second]", qc_stats_level[1]).replace("[third]", qc_stats_level[2]).replace("[ward]", ward_field)
#                 item_1_list = []
#                 item_0_list = []
#                 for item in queryset:
#                     if item[1] and item[1] not in item_1_list:
#                         item_1_list.append(item[1])
#                     if item[0] not in item_0_list:
#                         item_0_list.append(item[0])
#                     tmp = {ward_field: item[0] or "", "诊疗小组": item[1] or "", "医生姓名": item[2] or "",
#                            "总分": float(item[4]), "总数": int(item[3]),
#                            "{}数".format(qc_stats_level[0]): int(item[5]), "{}数".format(qc_stats_level[1]): int(item[6]),
#                            "{}数".format(qc_stats_level[2]): int(item[7])}
#                     data.append(tmp)
#                 total = len(data) + len(item_1_list) + len(item_0_list) + 1

#             return data, data_yaml, total

#     def get_disease_common_header_data(self, target_name, request):
#         result = []
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = StatsRepository.get_call_disease_sql(target_name, request)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("get_common_stats_diease_response, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             if target_name == "单病种分析病种统计":
#                 field_list = ['病种简称', '病种名称']
#                 field_list.extend(SINGLE_DISEASE_FIELD_LIST)
#             elif target_name == "单病种分析科室统计":
#                 field_list = ['科室编码', '科室名称', '覆盖病种数', '上报病种数']
#                 field_list.extend(SINGLE_DISEASE_FIELD_LIST)
#             if not queryset:
#                 return [{item: "" for item in field_list}], 0
#             for item in queryset:
#                 tmp = {}
#                 for index in range(len(field_list)):
#                     if '率' in field_list[index]:
#                         tmp[field_list[index]] = self.keep_one(item[index], True)
#                     elif '耗时' in field_list[index]:
#                         tmp[field_list[index]] = self.keep_one(item[index])
#                     else:
#                         tmp[field_list[index]] = item[index]
#                     tmp[field_list[index] + '_sort'] = item[index]
#                 result.append(tmp)
#             total = len(queryset)
#         return result, total

#     def get_disease_audit_common_header_data(self, target_name, request, front_year=0, indicator=None):
#         result = []
#         with self.context.app.mysqlConnection.session() as cursor:
#             call_proc_sql = StatsRepository.get_call_disease_qc_sql(target_name, request, front_year=front_year)
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("get_common_stats_disease_qc_response, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             if target_name == "病种质控总计":
#                 item = queryset[0]
#                 return {"病种数": item[0], "病例数": item[1], "maxDiseaseNum": self.keep_one(item[2]),
#                         "maxFatalityRate": self.keep_one(item[3]), "maxCost": self.keep_one(item[4]),
#                         "maxInHospDays": self.keep_one(item[5])}
#             if target_name == "病种类型统计":
#                 other = dict()
#                 for item in queryset:
#                     tmp = {}
#                     if not item[0]:
#                         continue
#                     tmp['病种类型'] = item[0]
#                     tmp['病种数'] = item[1]
#                     tmp['病例数'] = item[2]
#                     if '其他' in item[0]:
#                         other = tmp
#                         continue
#                     result.append(tmp)
#                 result.append(other)
#                 return result
#             if target_name == "雷达图":
#                 for item in queryset:
#                     tmp = {}
#                     tmp['病种英文'] = item[1] if item[1] else ''
#                     tmp['病种名称'] = item[2] if item[2] else ''
#                     tmp['单病种病历'] = item[3] if item[2] else 0
#                     tmp['病死率'] = item[4] if item[4] else 0
#                     tmp['例均费用'] = item[5] if item[5] else 0
#                     tmp['平均住院日'] = item[6] if item[6] else 0
#                     result.append(tmp)
#                 return result
#             if target_name == "通用质控指标":
#                 for item in queryset:
#                     tmp = {"kind": item[0], "name": item[1] or '', "value": self.keep_one(item[2]), "unit": item[3],
#                            "molecule": item[4] or '', "formula": item[5] or ''}
#                     result.append(tmp)
#                 return result
#             if target_name == "科室比较":
#                 for item in queryset:
#                     tmp = {}
#                     name = item[0]
#                     if not name: continue
#                     tmp['name'] = name
#                     tmp['num'] = item[1]
#                     if request.target != '覆盖病种数' and (request.department == '' or request.department=='全部科室') :
#                         tmp['allCase'] = item[2]
#                     result.append(tmp)
#                 result.sort(key=lambda a: a['num'], reverse=True)
#                 return result
#             if target_name == "趋势":
#                 for item in queryset:
#                     tmp = {}
#                     tmp['time'] = item[0]
#                     tmp['num'] = item[2] if request.target != '覆盖病种数' else item[1]
#                     if request.target != '覆盖病种数':
#                         tmp['allCase'] = item[1]
#                     result.append(tmp)
#                 return result
#             if target_name == "病种列表":
#                 for item in queryset:
#                     tmp = {}
#                     if indicator in SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_1:
#                         tmp = {"病种分类": item[0], "病种简称": item[1], "病种名称": item[2], "单病种病例": item[3], "上报成功": item[4],
#                                "应上报实上报率": self.keep_one(item[5], True)}
#                     if indicator in SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_2:
#                         tmp = {"就诊类型": item[0], "就诊号": item[1], "科室": item[2], "患者": item[3], "离院时间": item[4],
#                                "病种分类": item[5], "patientId": item[6], 'disease_id': item[7]}
#                     result.append(tmp)
#                 return result
#             if target_name == "病种质控统计":
#                 field_list = ['病种缩写', '病种名称']
#                 field_list.extend(SINGLE_DISEASE_QC_INDICATOR_FIELD_LIST)
#             if target_name == "科室质控统计":
#                 field_list = ['科室编码', '科室名称']
#                 field_list.extend(SINGLE_DISEASE_QC_FIELD_LIST)
#             if target_name == "医生质控统计":
#                 field_list = ['医生编码', '医生姓名', '科室编码', '科室名称']
#                 field_list.extend(SINGLE_DISEASE_QC_FIELD_LIST)
#             if target_name == "医生上报统计":
#                 field_list = ['医生编码','医生名称','科室编码', '科室名称', '覆盖病种数', '上报病种数']
#                 field_list.extend(SINGLE_DISEASE_FIELD_LIST)
#             if target_name == "填报统计":
#                 field_list = ['填报员编码', '填报员名称', '所在科室编码', '所在科室名称','覆盖病种数', '上报病种数']
#                 field_list.extend(SINGLE_DISEASE_QC_FIELD_LIST)
#             if target_name == "审核员统计":
#                 field_list = ['填报员编码', '审核员名称', '所在科室编码', '所在科室名称','覆盖病种数', '上报病种数']
#                 field_list.extend(SINGLE_DISEASE_QC_FIELD_LIST)
#             if target_name == "上报分析病种一览":
#                 return result
#             if target_name == "上报率统计表格":
#                 for item in queryset:
#                     tmp = {"就诊类型": item[0], "就诊号": item[1], "科室": item[2], "患者": item[3], "离院时间": item[4],
#                            "病种分类": item[5]}
#                     result.append(tmp)
#                 return result
#             if target_name == "上报时效分析":
#                 for item in queryset:
#                     tmp = {"就诊类型": item[0], "就诊号": item[1], "科室": item[2], "患者": item[3], "离院时间": item[4],
#                            "病种分类": item[5]}
#                     result.append(tmp)
#                 return result
#             if not queryset:
#                 tmp = {item: 0 for item in field_list}
#                 tmp["病种名称"] = ""
#                 tmp["病种缩写"] = ""
#                 return [tmp], 0
#             for item in queryset:
#                 tmp = {}
#                 for index in range(len(field_list)):
#                     # if '率' in field_list[index] or '占比' in field_list[index]:
#                     #     tmp[field_list[index]] = self.keep_one(item[index], True)
#                     # elif field_list[index] not in SINGLE_DISEASE_NO_SORT_FIELD:
#                     #     tmp[field_list[index]] = self.keep_one(item[index])
#                     # else:
#                     #     tmp[field_list[index]] = item[index]
#                     tmp[field_list[index]] = item[index]
#                     if not item[index]:
#                         tmp[field_list[index] + '_sort'] = 0
#                     else:
#                         tmp[field_list[index] + '_sort'] = float(item[index]) if isinstance(item[index], Decimal) else item[index]
#                 result.append(tmp)
#             total = len(queryset)
#         return result, total

#     @classmethod
#     def get_call_proc_sql(cls, target, request, sixMonth=0):
#         """
#         格式化存储过程
#         :return:
#         """
#         case_type_dict = {"running": "运行病历", "archived": "归档病历", "final": "终末病历"}
#         dept_type_dict = {1: "内科", 2: "外科", 0: "全部"}
#         stats_type_dict = {1: "qctype", 2: "deptkind", 3: "area"}
#         deptType = dept_type_dict[request.deptType]
#         caseType = case_type_dict.get(request.caseType, "全部类型")
#         department = request.department or "" if target != "医生成绩统计" else request.department or "全部科室"
#         doctorName = request.doctorName or "" if target != "医生成绩统计" else request.doctorName or "全部医生"
#         startTime = request.startTime
#         endTime = request.endTime
#         new_start_time = StatsRepository.get_start_time(endTime)
#         if sixMonth:
#             startTime = new_start_time
#             endTime = StatsRepository.get_end_time(endTime)
#         call_proc_sql = """call pr_case_expert('{target}','{caseType}','{startTime}','{endTime}','{branch}',
#         '{deptType}','{department}','{doctor}','','{statsType}')""".format(
#             target=target, caseType=caseType, startTime=startTime,
#             endTime=endTime, branch=request.branch or "全部院区", deptType=deptType,
#             department=department, doctor=doctorName, statsType=stats_type_dict[request.statsType or 3])
#         return call_proc_sql

#     def ExpertAllNum(self, request, context):
#         """
#         专家统计-全院成绩统计-全院质控数量概览
#         :param request:
#         :param context:
#         :return:
#         """
#         response = ExpertStatsPicCommonResponse()
#         call_proc_sql = self.get_call_proc_sql('全院质控数据统计', request, sixMonth=1)
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         level = 2
#         if request.level in qc_stats_level:
#             level += qc_stats_level.index(request.level) + 2
#         self.get_common_stats_pic_response(call_proc_sql, response, request, level=level)

#         return response

#     def ExpertAllLevel(self, request, context):
#         """
#         专家统计-全院成绩统计-质控情况分布
#         :param request:
#         :param context:
#         :return:
#         """
#         response = ExpertAllQcLevelResponse()
#         call_proc_sql = self.get_call_proc_sql('质控情况分布', request)
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(call_proc_sql)
#             self.logger.info("ExpertAllLevel, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             total = 0
#             first = 0
#             second = 0
#             third = 0
#             for item in queryset:
#                 total += item[1] or 0
#                 first += item[3] or 0
#                 second += item[4] or 0
#                 third += item[5] or 0
#             data = [first, second, third]
#             response.total = total
#             for i in range(len(data)):
#                 chartData = response.data.add()
#                 chartData.xData = qc_stats_level[i]
#                 chartData.yData = self.keep_one(data[i] / total * 100) if total else self.keep_one(0)
#         return response

#     def ExpertAllScorePic(self, request, context):
#         """
#         专家统计-全院成绩统计-全院质控成绩概览折线图
#         :param request:
#         :param context:
#         :return:
#         """
#         response = ExpertStatsPicCommonResponse()
#         call_proc_sql = self.get_call_proc_sql('全院质控数据统计', request, sixMonth=1)
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         level = 3
#         if request.level in qc_stats_level:
#             level += qc_stats_level.index(request.level) + 1
#         self.get_common_stats_pic_response(call_proc_sql, response, request, level=level, is_rate=1)

#         return response

#     def ExpertAllDetail(self, request, context):
#         """
#         专家统计-全院成绩统计-全院质控成绩概览
#         :return:
#         """
#         response = CommonHeaderDataResponse()
#         target_name = "质控情况分布"
#         to_web_data, data_yaml, total = self.get_common_header_data(target_name, request)

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         header, result = processor.toWeb(sortBy=[("总数", -1)], start=0, size=0)
#         self.format_header_data(response, header, result)

#         response.pageInfo.total = total
#         return response

#     def ExpertAllDetailExport(self, request, context):
#         """
#         专家统计-全院成绩统计-全院质控成绩概览导出
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()
#         target_name = "质控情况分布"
#         to_excel_data, data_yaml, total = self.get_common_header_data(target_name, request)

#         file_name = "全院质控成绩统计_{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sheet_name=target_name, sortBy=[("总数", -1)])

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def ExpertDeptScorePic(self, request, context):
#         """
#         专家统计-科室成绩统计-内外科成绩图
#         :return:
#         """
#         response = ExpertStatsPicCommonResponse()
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         target_name = "内外科科室成绩"
#         call_proc_sql = self.get_call_proc_sql(target_name, request)
#         self.logger.info("ExpertDeptScorePic, call_proc_sql: %s", call_proc_sql)
#         data = {}
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             for item in queryset:
#                 if item[0]:
#                     if not data.get(item[0], []):
#                         data[item[0]] = []
#                     level = 3
#                     if request.level in qc_stats_level:
#                         level += qc_stats_level.index(request.level) + 1
#                     level_data = self.keep_one(item[level])
#                     if level != 3:  # 甲乙丙率
#                         level_data = self.keep_one(item[level] / item[2] *  100)
#                     data[item[0]].append({"department": item[1] or "", "total": item[2] or 0,
#                                           "data": level_data})
#         for key, value in data.items():
#             protoItem = response.data.add()
#             protoItem.dataName = key
#             for item in value:
#                 detailItem = protoItem.items.add()
#                 detailItem.xData = item["department"]
#                 detailItem.yData = item["data"]
#         return response

#     def ExpertDeptScoreLevel(self, request, context):
#         """
#         专家统计-科室成绩统计-内外科成绩级别概览
#         :param request:
#         :param context:
#         :return:
#         """
#         response = ExpertDeptScoreLevelResponse()
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         level_list = ["first", "second", "third"]
#         qc_stats_level_dict = {qc_stats_level[i]: level_list[i] for i in range(len(qc_stats_level))}
#         target_name = "内外科科室成绩"
#         call_proc_sql = self.get_call_proc_sql(target_name, request)
#         self.logger.info("ExpertDeptScorePic, call_proc_sql: %s", call_proc_sql)
#         data = {"内科": {"total": 0, "first": 0, "second": 0, "third": 0}, "外科": {"total": 0, "first": 0, "second": 0, "third": 0}}
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             for item in queryset:
#                 if item[0]:
#                     data[item[0]]["total"] += int(item[2] or 0)
#                     data[item[0]]["first"] += int(item[4] or 0)
#                     data[item[0]]["second"] += int(item[5] or 0)
#                     data[item[0]]["third"] += int(item[6] or 0)
#         for key, value in data.items():
#             protoItem = response.items.add()
#             protoItem.deptType = key
#             protoItem.data.total = value["total"]
#             for item in qc_stats_level:
#                 levelItem = protoItem.data.data.add()
#                 levelItem.xData = item
#                 levelItem.yData = str(value[qc_stats_level_dict[item]])

#         return response

#     def ExpertDeptScoreList(self, request, context):
#         """
#         专家统计-科室成绩统计-内外科成绩列表
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonHeaderDataResponse()
#         target_name = "科室成绩概览"
#         to_web_data, data_yaml, total = self.get_common_header_data(target_name, request)

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = [("平均分", -1)]
#         if request.sortBy:
#             sort_by = [(request.sortBy, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=0, size=0)
#         self.format_header_data(response, header, result, not_sort_header=EXPERT_NO_SORT_FIELD)

#         response.pageInfo.total = total
#         response.pageInfo.start = request.start or 0
#         response.pageInfo.size = request.size or 15
#         return response

#     def ExpertDeptScoreDetail(self, request, context):
#         """
#         专家统计-科室成绩统计-内外科成绩列表内科室详情
#         :param request:
#         :param context:
#         :return:
#         """
#         response = ExpertDeptScoreDetailResponse()
#         target_name = "科室成绩概览月份数据"
#         qc_stats_level = self.context.app.config.get(Config.QC_STATS_LEVEL)
#         qc_stats_level = qc_stats_level.split(",")
#         level_dict = {"平均分": 2}
#         index = 3
#         for item in qc_stats_level:
#             level_dict[item] = index
#             index += 1
#         call_proc_sql = self.get_call_proc_sql(target_name, request)
#         self.logger.info("ExpertDeptScoreDetail, call_proc_sql: %s", call_proc_sql)
#         data = []
#         total = 0
#         data_yaml = EXPERT_DEPARTMENT_DETAIL_YAML.replace(
#             "[first]", qc_stats_level[0]).replace("[second]", qc_stats_level[1]).replace("[third]", qc_stats_level[2])
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(call_proc_sql)
#             queryset = query.fetchall()
#             for level in level_dict:
#                 pic_data = response.picData.data.add()
#                 pic_data.dataName = level
#                 index = level_dict[level]
#                 month_list = []
#                 for item in queryset:
#                     month_list.append(item[0])
#                 month_list.sort()
#                 for month in month_list:
#                     for item in queryset:
#                         if item[0] == month:
#                             pic_items = pic_data.items.add()
#                             pic_items.xData = item[0]
#                             pic_items.yData = str(item[index])
#             for item in queryset:
#                 tmp = {"时间": item[0], "总数": int(item[1]), "平均分": self.keep_one(item[2]), "%s数" % qc_stats_level[0]: int(item[3]),
#                        "%s数" % qc_stats_level[1]: int(item[4]),
#                        "%s数" % qc_stats_level[2]: int(item[5]), "sort_time": item[0].replace("-", ""),
#                        "%s率" % qc_stats_level[0]: self.keep_one(int(item[3]) / int(item[1]) * 100, True),
#                        "%s率" % qc_stats_level[1]: self.keep_one(int(item[4]) / int(item[1]) * 100, True),
#                        "%s率" % qc_stats_level[2]: self.keep_one(int(item[5]) / int(item[1]) * 100, True)}
#                 data.append(tmp)
#                 total += 1
#             if not queryset:
#                 append_dict = dict(EXPERT_DEPARTMENT_DETAIL_DATA, **EXPERT_LEVEL_DATA_1) if StatsRepository.verify_stats_level(qc_stats_level) \
#                     else dict(EXPERT_DEPARTMENT_DETAIL_DATA, **EXPERT_LEVEL_DATA_2)
#                 data.append(append_dict)

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, data)
#         sort_by = []
#         if request.sortBy:
#             field = request.sortBy if request.sortBy != "时间" else "sort_time"
#             sort_by = [(field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=0, size=0)
#         self.format_header_data(response.detailData, header, result, not_sort_header=EXPERT_NO_SORT_FIELD)
#         response.detailData.pageInfo.total = total
#         return response

#     def ExpertDeptScoreDetailExport(self, request, response):
#         """
#         专家统计-科室成绩统计-内外科成绩列表导出
#         :param request:
#         :param response:
#         :return:
#         """
#         response = FileData()
#         target_name = "科室成绩概览"
#         to_excel_data, data_yaml, total = self.get_common_header_data(target_name, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by = [(request.sortBy, request.sortWay)]

#         file_name = "科室成绩统计_{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name="科室成绩统计")

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def ExpertDoctorScore(self, request, response):
#         """
#         专家统计-医生成绩统计-查询
#         :param request:
#         :param response:
#         :return:
#         """
#         response = CommonHeaderDataResponse()
#         start = request.start or 0
#         size = request.size or 15
#         target_name = "医生成绩统计"
#         to_web_data, data_yaml, total = self.get_common_header_data(target_name, request)

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = [("平均分", -1)]
#         if request.sortBy:
#             sort_by = [(request.sortBy, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result)

#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExpertDoctorScoreExport(self, request, context):
#         """
#         专家统计-医生成绩统计-导出
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()
#         target_name = "医生成绩统计"
#         to_excel_data, data_yaml, total = self.get_common_header_data(target_name, request)

#         sort_by = []
#         if request.sortBy:
#             sort_by = [(request.sortBy, request.sortWay)]

#         file_name = "医生成绩统计_{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")

#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target_name)

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetUpdateTime(self, request, context):
#         """
#         专家统计-获取更新时间
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetUpdateTimeResponse()
#         result = self.getLastUpdateTime("expert")
#         updateDatetime = result.get("updateTime", None)
#         self.logger.info("lastUpdateTime: %s", updateDatetime)
#         if updateDatetime:
#             response.lastUpdateTime = updateDatetime.strftime('%Y-%m-%d %H:%M:%S') if updateDatetime else ""
#         return response

#     def GetStatsDiseaseList(self, request, context):
#         """单病种上报分析-病种分析列表"""
#         response = CommonHeaderDataResponse()
#         start = request.start or 0
#         size = request.size or 15
#         target_name = "单病种分析病种统计"
#         data_yaml = SINGLE_DISEASE_ANALYSE_YAML
#         to_web_data, total = self.get_disease_common_header_data(target_name, request)
#         if not to_web_data:
#             return
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result, is_sort=1, not_sort_header=SINGLE_DISEASE_NO_SORT_FIELD)
#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExportStatsDiseaseList(self, request, context):
#         """单病种上报分析-病种分析列表导出"""
#         response = FileData()
#         target_name = "单病种分析病种统计"
#         data_yaml = SINGLE_DISEASE_ANALYSE_YAML
#         to_excel_data, total = self.get_disease_common_header_data(target_name, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         file_name = "单病种分析病种统计{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target_name)

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsDiseaseDepartmentList(self, request, context):
#         """单病种上报分析-科室分析列表"""
#         response = CommonHeaderDataResponse()
#         start = request.start or 0
#         size = request.size or 15
#         target_name = "单病种分析科室统计"
#         data_yaml = SINGLE_DISEASE_DEPARTMENT_ANALYSE_YAML
#         to_web_data, total = self.get_disease_common_header_data(target_name, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result, is_sort=1, not_sort_header=SINGLE_DISEASE_NO_SORT_FIELD)
#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExportStatsDiseaseDepartmentList(self, request, context):
#         """单病种上报分析-科室分析列表导出"""
#         response = FileData()
#         target_name = "单病种分析科室统计"
#         data_yaml = SINGLE_DISEASE_DEPARTMENT_ANALYSE_YAML
#         to_excel_data, total = self.get_disease_common_header_data(target_name, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         file_name = "单病种科室分析{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target_name)

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsDiseaseDict(self, request, context):
#         """单病种上报分析-获取字典"""
#         response = GetStatsDiseaseDictResponse()
#         if not request.name:
#             return
#         sql = StatsRepository.get_call_disease_sql(request.name, only_dict=True)
#         result = []
#         with self.context.app.mysqlConnection.session() as cursor:
#             query = cursor.execute(sql)
#             objs = query.fetchall()
#             for obj in objs:
#                 if obj[0]:
#                     result.append(obj[0])
#             response.items.extend(result)
#         return response

#     def GetStatsDiseaseOverview(self, request, context):
#         """单病种质控分析-病种分析-病种一览"""
#         response = GetStatsDiseaseOverviewResponse()
#         target = "雷达图"
#         result = self.get_disease_audit_common_header_data(target, request)
#         s3 = '/_/paas/s3/object/disease/'
#         for item in result:
#             protoItem = response.items.add()
#             protoItem.name = item.get('病种名称', '')
#             protoItem.nameEng = item.get('病种英文', '')
#             protoItem.diseaseNum = str(item.get('单病种病历', ''))
#             protoItem.fatalityRate = str(item.get('病死率', ''))
#             protoItem.inHospDays = str(item.get('平均住院日', ''))
#             protoItem.cost = str(item.get('例均费用', ''))
#             protoItem.img = s3 + item.get('病种名称', '') + '.png'
#         return response

#     def GetStatsDiseaseOverviewMenu(self, request, context):
#         """单病种质控分析-病种分析-病种一览菜单统计"""
#         response = GetStatsDiseaseOverviewMenuResponse()
#         target_all = "病种质控总计"
#         target = '病种类型统计'
#         result_all_dict = self.get_disease_audit_common_header_data(target_all, request)
#         result_type = self.get_disease_audit_common_header_data(target, request)
#         max_result = self.get_disease_audit_common_header_data('雷达图', request)
#         maxDiseaseNum, maxFatalityRate, maxInHospDays, maxCost = 0, 0, 0, 0
#         for item in max_result:
#             if item['单病种病历'] > maxDiseaseNum: maxDiseaseNum = item['单病种病历']
#             if item['病死率'] > maxFatalityRate: maxFatalityRate = item['病死率']
#             if item['例均费用'] > maxCost: maxCost = item['例均费用']
#             if item['平均住院日'] > maxInHospDays: maxInHospDays = item['平均住院日']
#         response.diseaseNum = str(result_all_dict.get('病种数', '0'))
#         response.caseNum = str(result_all_dict.get('病例数', '0'))
#         response.maxDiseaseNum = str(maxDiseaseNum) if maxDiseaseNum else '0'
#         response.maxFatalityRate = str(maxFatalityRate) if maxFatalityRate else '0'
#         response.maxInHospDays = str(maxInHospDays) if maxInHospDays else '0'
#         response.maxCost = str(maxCost) if maxCost else '0'
#         for item in result_type:
#             protoItem = response.items.add()
#             protoItem.name = item.get('病种类型', '')
#             protoItem.diseaseNum = str(item.get('病种数', ''))
#             protoItem.caseNum = str(item.get('病例数', ''))
#         return response

#     def GetStatsDiseaseTargetDetail(self, request, context):
#         """单病种质控分析-病种分析-指标详情"""
#         response = GetStatsDiseaseTargetDetailResponse()
#         target_department = "科室比较"
#         target_trend = "趋势"
#         target = "病种列表"
#         indicator = request.target
#         result_department = self.get_disease_audit_common_header_data(target_department, request)
#         # 本期数据
#         result_trend = self.get_disease_audit_common_header_data(target_trend, request)
#         # 同期数据
#         front_result_trend = self.get_disease_audit_common_header_data(target_trend, request, front_year=1)
#         if indicator not in SINGLE_DISEASE_NOTABLE_FIELD:
#             to_web_data = self.get_disease_audit_common_header_data(target, request, indicator=indicator)
#             data_yaml = ''
#             if indicator in SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_1:
#                 data_yaml = SINGLE_DISEASE_QC_INDICATOR_TABLE_1
#             if indicator in SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_2:
#                 data_yaml = SINGLE_DISEASE_QC_INDICATOR_TABLE_2
#             if not data_yaml:
#                 return
#             cfg = BIFormConfig.fromYaml(data_yaml)
#             processor = BIDataProcess(cfg, to_web_data)
#             header, result = processor.toWeb()
#             self.format_header_data(response, header, result)
#         unmarshaldiseaseStatsDepartment(result_department, response, request.target, request.department)
#         unmarshaldiseaseStatsTrend(result_trend, response, request.target)
#         unmarshaldiseaseStatsTrend(front_result_trend, response, request.target, front_year=1)
#         return response

#     def GetStatsDiseaseTargetDetailMenu(self, request, context):
#         """单病种质控分析-病种分析-指标详情菜单"""
#         response = GetStatsDiseaseTargetDetailMenuResponse()
#         target = "通用质控指标"
#         have_disease = False if request.disease == '' or request.disease == '全部病种' else True
#         # 获取通用指标
#         result = self.get_disease_audit_common_header_data(target, request)
#         for item in result:
#             name = item['name']
#             kind = item['kind']
#             if have_disease and name == "覆盖病种数":
#                 continue
#             if '事中' in name:
#                 protoItem = response.items.add()
#             elif kind == '单病种特色指标':
#                 protoItem = response.featureItems.add()
#             else:
#                 protoItem = response.generalItems.add()
#             protoItem.name = name
#             protoItem.value = item['value']
#             protoItem.unit = item['unit']
#             protoItem.formula = item['formula']
#             protoItem.molecule = item['molecule']
#         return response

#     def ExportStatsDiseaseTargetDetail(self, request, context):
#         """单病种质控分析-病种分析-指标详情导出"""
#         response = FileData()
#         target = "病种列表"
#         indicator = request.target
#         to_web_data = self.get_disease_audit_common_header_data(target, request, indicator=indicator)
#         data_yaml = ''
#         if indicator in SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_1:
#             data_yaml = SINGLE_DISEASE_QC_INDICATOR_TABLE_1
#         if indicator in SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_2:
#             data_yaml = SINGLE_DISEASE_QC_INDICATOR_TABLE_2
#         if not data_yaml:
#             return
#         file_name = "病种列表{}指标统计{}".format(indicator, datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         processor.toExcel(path=path_file_name, sheet_name=indicator)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsDiseaseAuditDepartmentList(self, request, context):
#         """单病种质控分析-科室分析-科室质控统计"""
#         response = CommonHeaderDataResponse()
#         start = request.start or 0
#         size = request.size or 15
#         target = "科室质控统计"
#         data_yaml = SINGLE_DISEASE_QC_DEPARTMENT_YAML
#         to_web_data, total = self.get_disease_audit_common_header_data(target, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result, is_sort=1, not_sort_header=SINGLE_DISEASE_NO_SORT_FIELD)
#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExportStatsDiseaseAuditDepartmentList(self, request, context):
#         """单病种质控分析-科室分析-科室质控统计导出"""
#         response = FileData()
#         target = "科室质控统计"
#         data_yaml = SINGLE_DISEASE_QC_DEPARTMENT_YAML
#         to_excel_data, total = self.get_disease_audit_common_header_data(target, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         file_name = "科室质控统计{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsDiseaseAuditDoctorList(self, request, context):
#         """单病种质控分析-医生分析-医生质控统计"""
#         response = CommonHeaderDataResponse()
#         target = "医生质控统计"
#         start = request.start or 0
#         size = request.size or 15
#         data_yaml = SINGLE_DISEASE_QC_DOCTOR_YAML
#         to_web_data, total = self.get_disease_audit_common_header_data(target, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result, is_sort=1, not_sort_header=SINGLE_DISEASE_NO_SORT_FIELD)
#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExportStatsDiseaseAuditDoctorList(self, request, context):
#         """单病种质控分析-医生分析-医生质控统计导出"""
#         response = FileData()
#         target = "医生质控统计"
#         data_yaml = SINGLE_DISEASE_QC_DOCTOR_YAML
#         to_excel_data, total = self.get_disease_audit_common_header_data(target, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         file_name = "医生质控统计{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsDiseaseAuditIndicatorList(self, request, context):
#         """单病种质控分析-病种指标统计"""
#         response = CommonHeaderDataResponse()
#         target = '病种质控统计'
#         start = request.start or 0
#         size = request.size or 15
#         data_yaml = SINGLE_DISEASE_QC_INDICATOR_YAML
#         to_web_data, total = self.get_disease_audit_common_header_data(target, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result, is_sort=1, not_sort_header=SINGLE_DISEASE_NO_SORT_FIELD)
#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExportStatsDiseaseAuditIndicatorList(self, request, context):
#         """单病种质控分析-病种指标统计导出"""
#         response = FileData()
#         target = '病种质控统计'
#         data_yaml = SINGLE_DISEASE_QC_INDICATOR_YAML
#         to_excel_data, total = self.get_disease_audit_common_header_data(target, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         file_name = "病种指标统计{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsDiseaseContrast(self, request, context):
#         """对比分析"""
#         response = GetStatsDiseaseContrastResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             # 雷达图对比
#             data, radar_max, indicator_unit_dict = StatsRepository.get_disease_audit_contrast_common_header_data(session, request, "雷达")
#             unmarshaldiseaseContrastRadar(data, response)
#             # 折线图对比
#             data = StatsRepository.get_disease_audit_contrast_common_header_data(session, request)
#         unmarshaldiseaseContrastTrend(data, response)
#         for key, value in radar_max.items():
#             protoItem = response.maxRadar.add()
#             protoItem.key = key
#             protoItem.value = self.keep_one(value)
#             protoItem.unit = indicator_unit_dict.get(key, '')
#         return response

#     def GetStatsReportDiseaseOverview(self, request, context):
#         """单病种上报分析-病种一览"""
#         response = GetStatsReportDiseaseOverviewResponse()
#         target = "上报分析病种一览"
#         result = self.get_disease_audit_common_header_data(target, request)
#         s3 = '/_/paas/s3/object/disease/'
#         for item in result:
#             protoItem = response.items.add()
#             protoItem.name = item['name']
#             protoItem.diseaseNum = item['diseaseNum']
#             protoItem.chooseReport = item['chooseReport']
#             protoItem.submit = item['submit']
#             protoItem.audit = item['audit']
#             protoItem.report = item['report']
#             protoItem.successReport = item['successReport']
#             protoItem.caseNum = item['caseNum']
#             protoItem.reportRate = item['reportRate']
#             protoItem.img = s3 + item.get('病种名称', '') + '.png'
#         return response

#     def GetStatsReportRate(self, request, context):
#         """单病种上报分析-上报率统计"""
#         response = GetStatsReportRateResponse()
#         target = "上报率统计"
#         target_1 = "上报率统计表格"
#         data_yaml = SINGLE_DISEASE_ANALYSE_RATE_YAML
#         result_map = self.get_disease_common_header_data(target, request)
#         to_web_data, total = self.get_disease_audit_common_header_data(target_1, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         header, result = processor.toWeb()
#         self.format_header_data(response, header, result)
#         for item in result_map:
#             protoItem = response.items.add()
#             protoItem.key = item.get('key')
#             protoItem.diseaseNum = item.get('diseaseNum')
#             protoItem.rate = item.get('rate')
#         return response

#     def ExportStatsReportRate(self, request, context):
#         """单病种上报分析-上报率统计表格统计导出"""
#         response = FileData()
#         target = "上报率统计表格"
#         data_yaml = SINGLE_DISEASE_ANALYSE_RATE_YAML
#         to_excel_data, total = self.get_disease_audit_common_header_data(target, request)
#         file_name = "上报率统计{}".format(target, datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sheet_name=target)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetStatsReportAging(self, request, context):
#         """单病种上报分析-上报时效统计"""
#         response = GetStatsReportAgingResponse()
#         target = "上报时效统计"
#         # TODO 页面中圆盘数据及下方几个平均指标
#         data_yaml = SINGLE_DISEASE_ANALYSE_RATE_YAML
#         to_web_data, total = self.get_disease_audit_common_header_data(target, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         header, result = processor.toWeb()
#         self.format_header_data(response, header, result)
#         return response

#     def GetStatsDiseaseTable(self, request, context):
#         """单病种上报分析-医生-填报-审核员表格统计"""
#         response = CommonHeaderDataResponse()
#         start = request.start or 0
#         size = request.size or 15
#         data_yaml, target = '', ''
#         if request.type == "医生上报统计":
#             target = "医生上报统计"
#             data_yaml = SINGLE_DISEASE_DOCTOR_ANALYSE_YAML
#             self.get_disease_audit_common_header_data(target, request)
#         if request.type == "填报统计":
#             data_yaml = SINGLE_DISEASE_MEMBER_ANALYSE_YAML
#             target = "填报统计"
#         if request.type == "审核员统计":
#             data_yaml = SINGLE_DISEASE_AUDITOR_ANALYSE_YAML
#             target = "审核员统计"
#         if not data_yaml or target:
#             return
#         to_web_data, total = self.get_disease_audit_common_header_data(target, request)
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_web_data)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         header, result = processor.toWeb(sortBy=sort_by, start=start, size=size)
#         self.format_header_data(response, header, result, is_sort=1, not_sort_header=SINGLE_DISEASE_NO_SORT_FIELD)
#         response.pageInfo.total = total
#         response.pageInfo.start = start
#         response.pageInfo.size = size
#         return response

#     def ExportStatsDiseaseTable(self, request, context):
#         """单病种上报分析-医生-填报-审核员表格统计导出"""
#         response = FileData()
#         data_yaml, target = '', ''
#         if request.type == "医生上报统计":
#             target = "医生上报统计"
#             data_yaml = SINGLE_DISEASE_DOCTOR_ANALYSE_YAML
#             self.get_disease_audit_common_header_data(target, request)
#         if request.type == "填报统计":
#             data_yaml = SINGLE_DISEASE_MEMBER_ANALYSE_YAML
#             target = "填报统计"
#         if request.type == "审核员统计":
#             data_yaml = SINGLE_DISEASE_AUDITOR_ANALYSE_YAML
#             target = "审核员统计"
#         if not data_yaml or target:
#             return
#         to_excel_data, total = self.get_disease_audit_common_header_data(target, request)
#         sort_by = []
#         if request.sortBy:
#             sort_by_field = request.sortBy + "_sort"
#             sort_by = [(sort_by_field, request.sortWay)]
#         file_name = "{}{}".format(target,datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         cfg = BIFormConfig.fromYaml(data_yaml)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sortBy=sort_by, sheet_name=target)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetBranchTimelinessRate(self, request, context):
#         """
#         全院病案指标-病历书写时效性、诊疗行为符合率等
#         :param request:
#         :param context:
#         :return:
#         """
#         yaml_dict = {
#             1: BRANCH_TIMELINESS_RATE_YAML.format(branch='院区'),
#             2: BRANCH_TIMELINESS_RATE_YAML.format(branch='科室'),
#             3: DOCTOR_TIMELINESS_RATE_YAML,
#             4: BRANCH_TIMELINESS_RATE_YAML.format(branch='病区')
#         }
#         target_dict = {
#             1: '全院病案指标',
#             2: '科室病案指标',
#             3: '医生病案指标',
#             4: '病区病案指标'
#         }
#         target = target_dict.get(request.statusType,'')
#         if not target:
#             return
#         response = CommonHeaderDataResponse()
#         args = [target, request.startTime or "2000-01-01", request.endTime or "2030-12-31", request.branch or "全部",
#                 request.department or request.ward or "全部", request.attend or "全部"]
#         start = request.start or 0
#         size = request.size or 10
#         end = start + size

#         with self.context.app.mysqlConnection.session() as session:
#             call_proc_sql = """call pr_case_medical_index('%s','%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             self.logger.info("GetBranchTimelinessRate, call_proc_sql: %s", call_proc_sql)
#             query = session.execute(call_proc_sql)
#             queryset = query.fetchall()
#             total = sum([1 for item in queryset if item[0]])
#             retCols = query.keys()[:-1]
#             row_data = []
#             for item in queryset[start: end]:
#                 if not item[0]:
#                     continue
#                 tmp = {}
#                 for index in range(len(retCols)):
#                     tmp[retCols[index]] = str(item[index]).replace("--", "")
#                 row_data.append(tmp)
#             yaml_str = yaml_dict.get(request.statusType, None)
#             if not yaml_str:
#                 return
#             yaml_str = StatsRepository.get_branch_timeliness_yaml(yaml_str, self.context.app.config.get(Config.QC_STATS_BRANCH_TARGET_FIELD) or "")
#             cfg = BIFormConfig.fromYaml(yaml_str)
#             processor = BIDataProcess(cfg, row_data)
#             header, result = processor.toWeb()
#             self.format_header_data(response, header, result, first_title_dict=BRANCH_TIMELINESS_RATE_TARGET_FIRST_NAME_DICT)
#             response.pageInfo.total = total
#             response.pageInfo.size = size
#             response.pageInfo.start = start

#         return response

#     def GetBranchTimelinessRateExport(self, request, context):
#         """
#         全院病案指标-病历书写时效性、诊疗行为符合率等-导出
#         :param request:
#         :param context:
#         :return:
#         """
#         yaml_dict = {
#             1: BRANCH_TIMELINESS_RATE_YAML.format(branch='院区'),
#             2: BRANCH_TIMELINESS_RATE_YAML.format(branch='科室'),
#             3: DOCTOR_TIMELINESS_RATE_YAML,
#             4: BRANCH_TIMELINESS_RATE_YAML.format(branch='病区')
#         }
#         target_dict = {
#             1: '全院病案指标',
#             2: '科室病案指标',
#             3: '医生病案指标',
#             4: '病区病案指标'
#         }
#         response = FileData()
#         target = target_dict.get(request.statusType, '')
#         if not target:
#             return
#         args = [target, request.startTime or "2000-01-01", request.endTime or "2030-12-31", request.branch or "全部",
#                 request.department or request.ward or "全部", request.attend or "全部"]

#         with self.context.app.mysqlConnection.session() as session:
#             call_proc_sql = """call pr_case_medical_index('%s','%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = session.execute(call_proc_sql)
#             self.logger.info("GetBranchTimelinessRateExport, call_proc_sql: %s", call_proc_sql)
#             queryset = query.fetchall()
#             retCols = query.keys()[:-1]
#             row_data = []
#             for item in queryset:
#                 tmp = {}
#                 for index in range(len(retCols)):
#                     tmp[retCols[index]] = item[index]
#                 row_data.append(tmp)
#             yaml_str = yaml_dict.get(request.statusType, None)
#             if not yaml_str:
#                 return
#             yaml_str = StatsRepository.get_branch_timeliness_yaml(yaml_str, self.context.app.config.get(
#                 Config.QC_STATS_BRANCH_TARGET_FIELD) or "")
#             cfg = BIFormConfig.fromYaml(yaml_str)
#             processor = BIDataProcess(cfg, row_data)

#             file_name = "{}{}".format("全院病案指标", datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#             file_id = self.get_file_id(file_name)
#             path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#             processor.toExcel(path=path_file_name, sheet_name="全院病案指标")
#             response.id = file_id
#             response.fileName = file_name
#             return response

#     def GetBranchTimelinessRateDetail(self, request, context):
#         """
#         全院病案指标-指标明细
#         :param request:
#         :param context:
#         :return:
#         """
#         response = CommonHeaderDataResponse()
#         target_field = BRANCH_TARGET_FIELD_DICT.get(request.targetName)
#         if not target_field:
#             self.logger.error("request.targetName: %s is error.", request.targetName)
#             return

#         with self.context.app.mysqlConnection.session() as session:
#             to_web_data, total = StatsRepository.GetBranchTimelinessRateData(session, request, target_field)
#         yaml_conf = BRANCH_TIMELINESS_DETAIL_LIST_YAML
#         if request.targetName in ("入院记录24小时内完成率", "手术记录24小时内完成率", "出院记录24小时内完成率", "病案首页24小时内完成率"):
#             yaml_conf = BRANCH_TIMELINESS_DETAIL_TIME_LIST_YAML
#         cfg = BIFormConfig.fromYaml(yaml_conf)
#         processor = BIDataProcess(cfg, to_web_data)
#         header, result = processor.toWeb()
#         self.format_header_data(response, header, result)

#         response.pageInfo.start = request.start or 0
#         response.pageInfo.size = request.size or 10
#         response.pageInfo.total = total
#         return response

#     def GetBranchTimelinessRateDetailExport(self, request, context):
#         """
#         全院病案指标-指标明细-导出
#         :param request:
#         :param context:
#         :return:
#         """
#         response = FileData()
#         target_field = BRANCH_TARGET_FIELD_DICT.get(request.targetName)
#         if not target_field:
#             self.logger.error("request.targetName: %s is error.", request.targetName)
#             return

#         with self.context.app.mysqlConnection.session() as session:
#             to_excel_data, total = StatsRepository.GetBranchTimelinessRateData(session, request, target_field, is_export=1)
#         yaml_conf = BRANCH_TIMELINESS_DETAIL_LIST_YAML
#         if request.targetName in ("入院记录24小时内完成率", "手术记录24小时内完成率", "出院记录24小时内完成率", "病案首页24小时内完成率"):
#             yaml_conf = BRANCH_TIMELINESS_DETAIL_TIME_LIST_YAML
#         cfg = BIFormConfig.fromYaml(yaml_conf)
#         processor = BIDataProcess(cfg, to_excel_data)

#         file_name = "【{}】{}{}".format(request.targetName, "指标明细", datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         processor.toExcel(path=path_file_name, sheet_name=request.targetName)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def GetBranchTimelinessRateDetailFormula(self, request, context):
#         """
#         全院病案指标-指标明细-公式数据
#         :param request:
#         :param context:
#         :return:
#         """
#         target_dict = {
#             1: '全院病案指标',
#             2: '科室病案指标',
#             3: '医生病案指标',
#             4: '病区病案指标'
#         }
#         dimension_dict = {
#             1: 'branch',
#             2: 'department',
#             3: 'attend',
#             4: 'ward'
#         }
#         response = GetBranchTimelinessRateDetailFormulaResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             dept_or_ward = request.department or request.ward or "全部"
#             if dept_or_ward == "总计":
#                 dept_or_ward = "全部"
#             args = [target_dict.get(request.statusType), request.startTime or "2000-01-01", request.endTime or "2030-12-31",
#                     request.branch if request.branch and request.branch != "全院" else "全部",
#                     dept_or_ward, request.attend if request.attend and request.attend != "总计" else "全部"]
#             call_proc_sql = """call pr_case_medical_index('%s','%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = session.execute(call_proc_sql)
#             queryset = query.fetchall()
#             retCols = query.keys()[:-1]
#             find_col = False
#             col_current = 3 if not request.attend else 4
#             for col in range(col_current, len(retCols), 3):
#                 if retCols[col] == request.targetName:
#                     col_current = col
#                     find_col = True
#             if not find_col:
#                 return
#             dim = dimension_dict.get(request.statusType)
#             dim_value = getattr(request, dim, '总计')
#             select_index = 0 if dim != 'attend' else 1
#             for item in queryset:
#                 if item[select_index] == dim_value:
#                     response.moleculeNum = str(item[col_current-2] or 0)
#                     response.denominatorNum = str(item[col_current-1] or 0)
#                     break

#             query_formula_sql = '''select mumerator, denominator from dim_firstpageindex where name = "%s"''' % request.targetName
#             query = session.execute(query_formula_sql)
#             queryset = query.fetchone()
#             if queryset:
#                 response.molecule = queryset[0]
#                 response.denominator = queryset[1]

#         return response

#     def GetMonthArchivingRate(self, request, context):
#         """
#         统计科室归档率-按月份统计
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetMonthArchivingRateResponse()
#         endTime = request.endTime or datetime.now().strftime("%Y-%m-%d")
#         startTime = StatsRepository.get_year_start_time(endTime)
#         args = [startTime, endTime, "month", request.branch or "全部", request.department or "全部", "全部", "全部"]

#         with self.context.app.mysqlConnection.session() as session:
#             call_proc_sql = """call pr_case_archiverate('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % tuple(args)
#             query = session.execute(call_proc_sql)
#             queryset = query.fetchall()
#             for item in queryset:
#                 protoItem = response.data.add()
#                 protoItem.month = item[0]
#                 protoItem.archivingRate = self.keep_one(item[1])
#                 protoItem.archivingRate2 = self.keep_one(item[2])
#                 protoItem.archivingRate3 = self.keep_one(item[3])
#                 protoItem.archivingRate7 = self.keep_one(item[4])

#         return response

#     def StatsDefectRateList(self, request, context):
#         """
#         质控分析-缺陷率统计-查询
#         :return:
#         """
#         response = StatsDefectRateListResponse()
#         if not request.type or request.type not in ("科室", "病区"):
#             self.logger.error("StatsDefectRateList, request.type: %s is error.", request.type)
#             return response
#         start = request.start or 0
#         size = request.size or 10
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)
#         data = self.get_defect_rate_data(request, is_need_group)
#         response.total = len(data)
#         response.start = start
#         response.size = size
#         for item in data[start: start + size]:
#             protoItem = response.data.add()
#             protoItem.department = item.get("dept") or ""
#             protoItem.ward = item.get("dept") or ""
#             protoItem.group = item.get("group") or ""
#             protoItem.attend = item.get("attend") or ""
#             protoItem.applyCaseNum = item.get("apply_num") or 0
#             protoItem.applyUnqualifiedNum = item.get("defect_num") or 0
#             protoItem.defectRate = self.keep_one(protoItem.applyUnqualifiedNum / protoItem.applyCaseNum * 100, True) if protoItem.applyCaseNum else "0%"
#             protoItem.departmentHide = item.get("deptHide") or ""
#             protoItem.wardHide = item.get("deptHide") or ""
#             protoItem.groupHide = item.get("groupHide") or ""
#             protoItem.attendHide = item.get("attendHide") or ""

#         return response

#     def get_defect_rate_data(self, request, is_need_group=1):
#         """
#         获取缺陷率统计数据
#         :return:
#         """
#         dept = request.department or "全部"
#         if dept == "总计":
#             dept = "全部"
#         ward = request.ward or "全部"
#         if ward == "总计":
#             ward = "全部"
#         args = ["{}缺陷率统计".format(request.type), request.startTime, request.endTime, request.branch or "全部院区",
#                 dept, ward, request.group or "全部", request.attend or "全部"]
#         with self.context.app.mysqlConnection.session() as session:
#             call_sql = "call pr_case_rate('%s','%s','%s','%s','%s','%s','%s','%s');" % tuple(args)
#             self.logger.info("StatsDefectRateList, call_sql: %s", call_sql)
#             query = session.execute(call_sql)
#             queryset = query.fetchall()
#             data = StatsRepository.format_defect_rate_data(queryset, request, is_need_group)
#         return data

#     def StatsDefectRateExport(self, request, context):
#         """
#         质控分析-缺陷率统计-导出
#         :return:
#         """
#         response = FileData()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)
#         data = self.get_defect_rate_data(request, is_need_group)
#         file_name = "{}至{}缺陷率统计".format(request.startTime[:10], request.endTime[:10]) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#         if request.type == "科室":
#             if is_need_group == 1:
#                 title = DEFECT_RATE_TITLE_DEPT
#             else:
#                 title = DEFECT_RATE_TITLE_DEPT_NO_GROUP
#         else:
#             title = DEFECT_RATE_TITLE_WARD
#         StatsRepository.write_defect_rate_excel(title, data, path_file_name)
#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def StatsDefectRateDetailList(self, request, context):
#         """
#         质控分析-缺陷率统计-明细-查询
#         :return:
#         """
#         response = StatsDefectRateDetailListResponse()
#         case_model = self.context.app.mysqlConnection["case"]
#         with self.context.app.mysqlConnection.session() as session:
#             total, data = StatsRepository.get_defect_rate_detail_data(session, case_model, request)
#             response.total = total
#             response.start = request.start or 0
#             response.size = request.size or 10

#             for item, case in data:
#                 protoItem = response.data.add()
#                 protoItem.caseId = item.caseid or ""
#                 protoItem.patientId = case.inpNo or case.patientId or ""
#                 protoItem.name = item.name or ""
#                 protoItem.admitTime = item.admittime.strftime("%Y-%m-%d") if item.admittime else ""
#                 protoItem.dischargeTime = item.dischargetime.strftime("%Y-%m-%d") if item.dischargetime else ""
#                 protoItem.department = item.outdeptname or ""
#                 protoItem.group = item.medicalgroupname or ""
#                 protoItem.ward = item.outhosward or ""
#                 protoItem.attend = item.attendDoctor or ""
#                 protoItem.score = str(item.score or 0)
#                 protoItem.isQualified = item.is_standard or ""
#                 protoItem.status = item.status or 0
#                 protoItem.statusName = parseStatusName(False, item.status)

#         return response

#     def StatsDefectRateDetailExport(self, request, context):
#         """
#         质控分析-缺陷率统计-明细-导出
#         :return:
#         """
#         response = FileData()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)
#         case_model = self.context.app.mysqlConnection["case"]
#         with self.context.app.mysqlConnection.session() as session:
#             total, data = StatsRepository.get_defect_rate_detail_data(session, case_model, request, is_export=1)
#             if request.type == "科室":
#                 if is_need_group == 1:
#                     title = DEFECT_RATE_DETAIL_TITLE_DEPT
#                 else:
#                     title = DEFECT_RATE_DETAIL_TITLE_DEPT_NO_GROUP
#             else:
#                 title = DEFECT_RATE_DETAIL_TITLE_WARD
#             title_name = StatsRepository.get_defect_rate_detail_export_title_name(request)
#             file_name = "{}至{}【{}】明细".format(request.startTime[:10], request.endTime[:10], title_name) + ".xlsx"
#             file_id = self.get_file_id(file_name)
#             path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")
#             StatsRepository.write_defect_detail_excel(title, data, path_file_name)
#             response.id = file_id
#             response.fileName = file_name
#         return response

#     def StatsDefectRateUpdateStatus(self, request, context):
#         """
#         质控分析-缺陷率统计-更新状态查询
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetStatsDataUpdateStatusResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             query_sql = '''select updatetime, updatestatus from case_updatestatus_rate'''
#             query = session.execute(query_sql)
#             data = query.fetchone()
#             response.status = int(data[1] if data else 2)
#             last_time = data[0] + timedelta(hours=8) if data else datetime(year=2022, month=1, day=1)
#             response.lastUpdateTime = last_time.strftime('%Y-%m-%d %H:%M:%S') if data else ""
#         return response

#     def StatsDefectRateUpdate(self, request, context):
#         """
#         质控分析-缺陷率统计-更新数据
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsDataUpdateResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             call_sql = '''call pr_case_rate_process('','') '''
#             session.execute(call_sql)
#             session.commit()
#             response.isSuccess = True
#         return response

#     def StatsArchivedQualityList(self, req, context):
#         """质控分析-归档病历质量统计-查询
#         """
#         response = StatsArchivedQualityListResponse()
#         if not req.type or req.type not in ("科室", "病区"):
#             self.logger.error("StatsDefectRateList, request.type: %s is error.", req.type)
#             return response
#         start = req.start or 0
#         size = req.size or 10

#         data = []
#         with self.context.app.mysqlConnection.session() as session:
#             group_flag = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) == 1
#             data = ArchivedQualityStats(req.type, req.branch, req.department, req.group, req.ward, req.attend, req.startTime, req.endTime).stats(session, group_flag)

#         response.total = len(data)
#         response.start = start
#         response.size = size
#         for item in data[start: start + size]:
#             protoItem = response.data.add()
#             if item.attend:
#                 protoItem.attend = item.attend or ""
#             elif item.group:
#                 protoItem.group = item.group or ""
#             else:
#                 protoItem.department = item.dept or ""
#                 protoItem.ward = item.ward or ""
#             protoItem.archivedNum = int(item.data[0]) or 0
#             protoItem.finishedNum = int(item.data[1]) or 0
#             protoItem.averageScore = self.keep_one(item.data[2])
#             protoItem.sampleRate = self.keep_one(item.data[3] * 100, True)
#             protoItem.firstNum = int(item.data[4])
#             protoItem.firstAvgScore = self.keep_one(item.data[5])
#             protoItem.firstRate = self.keep_one(item.data[6] * 100, True)
#             protoItem.secondNum = int(item.data[7])
#             protoItem.secondAvgScore = self.keep_one(item.data[8])
#             protoItem.secondRate = self.keep_one(item.data[9] * 100, True)
#             protoItem.thirdNum = int(item.data[10])
#             protoItem.thirdAvgScore = self.keep_one(item.data[11])
#             protoItem.thirdRate = self.keep_one(item.data[12] * 100, True)
#             protoItem.departmentHide = req.department if item.dept == "总计" else (item.dept or "")
#             protoItem.wardHide = req.ward if item.ward == "总计" else (item.ward or "")
#             protoItem.groupHide = item.group or req.group or ""
#             protoItem.attendHide = item.attend or req.attend or ""
#         return response

#     def StatsArchivedQualityExport(self, req, context):
#         """
#         质控分析-归档病历质量统计-导出
#         """
#         response = FileData()
#         file_name = "{}至{}归档病历质量统计".format(req.startTime[:10], req.endTime[:10]) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")

#         header = ["科室", "诊疗组", "责任医生", "已归档病历数", "质控病历数", "总分", "甲级病历数", "甲级病历总分", "乙级病历数", "乙级病历总分", "丙级病历数", "丙级病历总分"]
#         if req.type == "科室" and int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) == 1:
#             header = ["科室", "责任医生", "已归档病历数", "质控病历数", "总分", "甲级病历数", "甲级病历总分", "乙级病历数", "乙级病历总分", "丙级病历数", "丙级病历总分"]
#         if req.type == "病区":
#             header = ["病区", "责任医生", "已归档病历数", "质控病历数", "总分", "甲级病历数", "甲级病历总分", "乙级病历数", "乙级病历总分", "丙级病历数", "丙级病历总分"]

#         with self.context.app.mysqlConnection.session() as session:
#             stats = ArchivedQualityStats(req.type, req.branch, req.department, req.group, req.ward, req.attend, req.startTime, req.endTime)
#             stats.export_excel(session, header, path_file_name)

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def StatsArchivedQualityDetailList(self, req, context):
#         """
#         质控分析-归档病历质量统计-明细-查询
#         :return:
#         """
#         response = StatsArchivedQualityDetailListResponse()
#         case_model = self.context.app.mysqlConnection["case"]
#         with self.context.app.mysqlConnection.session() as session:
#             stats = ArchivedQualityStats(req.type, req.branch, req.department, req.group, req.ward, req.attend, req.startTime, req.endTime)
#             total, data = stats.detail(session, case_model, req)
#             response.total = total
#             response.start = req.start or 0
#             response.size = req.size or 10

#             for item, case in data:
#                 protoItem = response.data.add()
#                 protoItem.caseId = item.caseid or ""
#                 protoItem.patientId = case.inpNo or case.patientId or ""
#                 protoItem.name = item.name or ""
#                 protoItem.admitTime = item.admittime.strftime("%Y-%m-%d") if item.admittime else ""
#                 protoItem.dischargeTime = item.dischargetime.strftime("%Y-%m-%d") if item.dischargetime else ""
#                 protoItem.department = item.outdeptname or ""
#                 protoItem.group = item.medicalgroupname or ""
#                 protoItem.ward = item.wardname or ""
#                 protoItem.attend = item.attendDoctor or ""
#                 protoItem.score = str(item.score or 0)
#                 protoItem.isFinished = item.is_mq or ""
#                 protoItem.level = {"甲": "甲级", "乙": "乙级", "丙": "丙级"}.get(item.caselevel, item.caselevel) or ""

#         return response

#     def StatsArchivedQualityDetailExport(self, req, context):
#         """
#         质控分析-归档病历质量统计-明细-导出
#         :return:
#         """
#         response = FileData()
#         case_model = self.context.app.mysqlConnection["case"]
#         with self.context.app.mysqlConnection.session() as session:
#             title_name = StatsRepository.get_defect_rate_detail_export_title_name(req)
#             file_name = "{}至{}【{}】明细".format(req.startTime[:10], req.endTime[:10], title_name) + ".xlsx"
#             file_id = self.get_file_id(file_name)
#             path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")

#             stats = ArchivedQualityStats(req.type, req.branch, req.department, req.group, req.ward, req.attend, req.startTime, req.endTime)
#             total, data = stats.detail(session, case_model, req, is_export=True)

#             header = ["病历号", "姓名", "入院日期", "出院日期", "科室", "责任医生", "是否质控", "病历等级", "病历分数"]
#             if req.type == "科室" and int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) == 1:
#                 header = ["病历号", "姓名", "入院日期", "出院日期", "科室", "诊疗组", "责任医生", "是否质控", "病历等级", "病历分数"]
#             if req.type == "病区":
#                 header = ["病历号", "姓名", "入院日期", "出院日期", "病区", "责任医生", "是否质控", "病历等级", "病历分数"]

#             stats.write_detail_excel(header, data, path_file_name)

#             response.id = file_id
#             response.fileName = file_name
#         return response

#     def StatsArchivedQualityUpdateStatus(self, request, context):
#         """
#         质控分析-归档病历质量统计-更新状态查询
#         """
#         response = GetStatsDataUpdateStatusResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             query_sql = '''select updatetime, updatestatus from case_archive_extend_updatestatus '''
#             query = session.execute(query_sql)
#             data = query.fetchone()
#             response.status = int(data[1] if data else 2)
#             response.lastUpdateTime = arrow.get(data[0] if data else "2022-01-01").to('+08:00').strftime('%Y-%m-%d %H:%M:%S')
#         return response

#     def StatsArchivedQualityUpdate(self, request, context):
#         """
#         质控分析-归档病历质量统计-更新数据
#         """
#         response = StatsDataUpdateResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             call_sql = '''call pr_case_archivecase_process('','') '''
#             session.execute(call_sql)
#             response.isSuccess = True
#         return response

#     def StatsRunningCaseNum(self, request, context):
#         """
#         质控分析-事中质控情况分析-病历数、累计减少问题数、平均病历减少问题数
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_running_case_info(session, request, response)
#             StatsRepository.get_running_problem_info(session, request, response)
#         return response

#     def StatsRunningDeptTop(self, request, context):
#         """
#         质控分析-事中质控情况分析-问题改善科室TOP10
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_running_dept_top(session, request, response)
#         return response

#     def StatsRunningDeptInfo(self, request, context):
#         """
#         质控分析-事中质控情况分析-对应科室问题改善诊疗组、医生TOP10情况
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_running_dept_info(session, request, response, is_need_group)
#         return response

#     def StatsRunningType(self, request, context):
#         """
#         质控分析-事中质控情况分析-各类别问题改善情况分析
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_running_type(session, request, response)
#         return response

#     def StatsRunningTypeInfo(self, request, context):
#         """
#         质控分析-事中质控情况分析-对应类别问题改善情况分析
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_running_type_info(session, request, response)
#         return response

#     def StatsArchiveCaseNumInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-病历数、病历缺陷率、平均每病案缺陷数
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_case_num(session, request, response)
#         return response

#     def StatsArchiveRatioInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-病历质量趋势分析、病历问题数量趋势分析
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_ratio_info(session, request, response)
#         return response

#     def StatsArchiveDeptTopInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-病历质量重点关注科室top10
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_dept_top_info(session, request, response)
#         return response

#     def StatsArchiveDoctorTopInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-对应科室-病历质量重点关注医生top10
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) == 1
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_doctor_top_info(session, request, response, is_need_group)
#         return response

#     def StatsArchiveProblemNumTopInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-病历问题数量重点关注科室top10
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_problem_num_top(session, request, response)
#         return response

#     def StatsArchiveProblemNumDoctorTopInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-对应科室-问题数量重点关注医生top10
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) == 1
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_problem_num_doctor_top(session, request, response, is_need_group)
#         return response

#     def StatsArchiveProblemTypeInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-问题所属类别分析
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_problem_type(session, request, response)
#         return response

#     def StatsArchiveProblemNumInfo(self, request, context):
#         """
#         质控分析-事后质控情况分析-问题触发数量分析
#         :param request:
#         :param context:
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_archive_problem_num_info(session, request, response)
#         return response

#     def GetWorkloadReport(self, request, context):
#         """工作量统计报表
#         """
#         response = CommonHeaderDataResponse()
#         args = [request.branch or "全部院区", request.department or "全部科室", request.startTime, request.endTime]
#         title = ["科室", "出院人数", "提交质控病案数", "科室质控病案数", "科室质控病案比例", "院级质控病案数", "院级质控病案比例", "首页质控病案数", "首页质控病案比例", "总质控数量", "总体病案质控比例",
#                  "甲级病案数", "乙级病案数", "丙级病案数", "甲级率", "输血患者人数", "科室输血病案质控人数", "科室输血病案质控比例", "院级输血病案质控数", "院级输血病案质控比例",
#                  "死亡患者人数", "科室死亡病案质控数", "科室死亡病案质控比例", "院级死亡病案质控数", "院级死亡病案质控比例", "超30天患者人数", "科室超30天病案质控数",
#                  "科室超30天病案质控比例", "院级超30天病案质控数", "院级超30天病案质控比例"]
#         to_web_data = []
#         total = 0
#         with self.context.app.mysqlConnection.session() as session:
#             call_proc_sql = """call pr_case_report('%s', '%s', '%s', '%s')""" % tuple(args)
#             query = session.execute(call_proc_sql)
#             queryset = query.fetchall()
#             for item in queryset:
#                 row_data = {}
#                 for index in range(len(title)):
#                     if "比例" in title[index]:
#                         row_data[title[index]] = item[index] or 0
#                     else:
#                         row_data[title[index]] = item[index]
#                 to_web_data.append(row_data)
#                 total += 1
#         cfg = BIFormConfig.fromYaml(WORKLOAD_REPORT_YAML)
#         processor = BIDataProcess(cfg, to_web_data)
#         header, result = processor.toWeb(start=request.start, size=request.size)
#         self.format_header_data(response, header, result)

#         response.pageInfo.start = request.start or 0
#         response.pageInfo.size = request.size or 10
#         response.pageInfo.total = total
#         return response

#     def ExportWorkloadReport(self, request, context):
#         """工作量报表导出"""
#         response = FileData()

#         file_name = "工作量报表_{}".format(datetime.now().strftime("%Y-%m-%d")) + ".xlsx"
#         file_id = self.get_file_id(file_name)
#         path_file_name = os.path.join(self.privateDataPath, file_id + ".xlsx")

#         args = [request.branch or "全部院区", request.department or "全部科室", request.startTime, request.endTime]
#         to_excel_data = []

#         with self.context.app.mysqlConnection.session() as session:
#             call_proc_sql = """call pr_case_report('%s', '%s', '%s', '%s')""" % tuple(args)
#             query = session.execute(call_proc_sql)
#             queryset = query.fetchall()
#             title = ["科室", "出院人数", "提交质控病案数", "科室质控病案数", "科室质控病案比例", "院级质控病案数", "院级质控病案比例", "首页质控病案数", "首页质控病案比例", "总质控数量", "总体病案质控比例",
#                      "甲级病案数", "乙级病案数", "丙级病案数", "甲级率", "输血患者人数", "科室输血病案质控人数", "科室输血病案质控比例", "院级输血病案质控数", "院级输血病案质控比例",
#                      "死亡患者人数", "科室死亡病案质控数", "科室死亡病案质控比例", "院级死亡病案质控数", "院级死亡病案质控比例", "超30天患者人数", "科室超30天病案质控数",
#                      "科室超30天病案质控比例", "院级超30天病案质控数", "院级超30天病案质控比例"]
#             for item in queryset:
#                 row_data = {}
#                 for index in range(len(title)):
#                     if "比例" in title[index]:
#                         row_data[title[index]] = item[index] or 0
#                     else:
#                         row_data[title[index]] = item[index]
#                 to_excel_data.append(row_data)
#         cfg = BIFormConfig.fromYaml(WORKLOAD_REPORT_YAML)
#         processor = BIDataProcess(cfg, to_excel_data)
#         processor.toExcel(path=path_file_name, sheet_name="工作量报表")

#         response.id = file_id
#         response.fileName = file_name
#         return response

#     def StatsVetoBaseInfo(self, request, context):
#         """
#         质控分析-强制拦截情况分析-病历拦截率、强制拦截数、累计减少问题数
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_veto_base_info(session, request, response)
#         return response

#     def StatsVetoCaseTrendInfo(self, request, context):
#         """
#         质控分析-强制拦截情况分析-病历强制拦截率趋势分析、累计减少强制问题数趋势分析
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_veto_case_trend_info(session, request, response)
#         return response

#     def StatsVetoDeptTopInfo(self, request, context):
#         """
#         质控分析-强制拦截情况分析-病历强制拦截率科室top10
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_veto_dept_top_info(session, request, response)
#         return response

#     def StatsVetoDoctorTopInfo(self, request, context):
#         """
#         质控分析-强制拦截情况分析-对应科室医生top10
#         :return:
#         """
#         response = StatsCommonResponse()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_veto_doctor_top_info(session, request, response, is_need_group)
#         return response

#     def StatsVetoProblemTypeInfo(self, request, context):
#         """
#         质控分析-强制拦截情况分析-问题所属类别分析
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_veto_problem_type_info(session, request, response)
#         return response

#     def StatsVetoProblemNumInfo(self, request, context):
#         """
#         质控分析-强制拦截情况分析-对应问题所属类别数量分析
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_veto_problem_num_info(session, request, response)
#         return response

#     def StatsRefuseCaseNumInfo(self, request, context):
#         """
#         质控分析-病历退回情况分析-退回病历数、退回率
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_refuse_case_num_info(session, request, response)
#         return response

#     def StatsRefuseRatioInfo(self, request, context):
#         """
#         质控分析-病历退回情况分析-病历退回率、退回病历数分析
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_refuse_ratio_info(session, request, response)
#         return response

#     def StatsRefuseDeptTopInfo(self, request, context):
#         """
#         质控分析-病历退回情况分析-病历退回科室top10
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_refuse_dept_top_info(session, request, response)
#         return response

#     def StatsRefuseDoctorTopInfo(self, request, context):
#         """
#         质控分析-病历退回情况分析-对应科室重点关注医生top10
#         :return:
#         """
#         response = StatsCommonResponse()
#         is_need_group = int(self.context.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_refuse_doctor_top_info(session, request, response, is_need_group)
#         return response

#     def StatsRefuseProblemTypeInfo(self, request, context):
#         """
#         质控分析-病历退回情况分析-问题所属类别分析
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_refuse_problem_type_info(session, request, response)
#         return response

#     def StatsRefuseProblemNumInfo(self, request, context):
#         """
#         质控分析-病历退回情况分析-问题触发数量分析
#         :return:
#         """
#         response = StatsCommonResponse()
#         with self.context.app.mysqlConnection.session() as session:
#             StatsRepository.get_refuse_problem_num_info(session, request, response)
#         return response
