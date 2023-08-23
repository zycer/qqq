# import logging
# import time

# from iyoudoctor.hosp.qc.v3.qccdss.service_pb2_grpc_wrapper import QCCDSSManagerServicer as _QCCDSSManagerServicer
# from iyoudoctor.hosp.qc.v3.qccdss.service_message_pb2 import GetCaseLabExamInfoResponse, GetDoctorCaseListResponse, \
#     GetPatientPortraitResponse, GetQcAuditDataByCaseIdResponse, GetParserResultResponse
# from qcaudit.domain.case.req import GetEmrListRequest, GetOrderListRequest, GetAssayListRequest, GetExamListRequest
# from qcaudit.domain.qccdss.req import GetAuditInfoBaseRequest
# from qcaudit.service.protomarshaler import unmarshalCaseLabExamInfo
# from qcaudit.utils.qccdss_protomarshaler import unmarshalQcAuditData, QCunmarshalCaseInfo, QCunmarshalFirstPageInfo
# from qcaudit.common.const import AUDIT_TYPE_HOSPITAL
# from qcaudit.domain.doctor.doctor_repository import DoctorRepository
# from qcaudit.domain.qccdss.qccdssrepository import QCCdssRepository
# from datetime import datetime
# import requests
# from google.protobuf.struct_pb2 import Struct
# # import grpc
# from redis import Redis
# from google.protobuf.json_format import MessageToDict
# import json


# class QCCDSSManagerServicer(_QCCDSSManagerServicer):
#     """ 质控-CDSS 相关接口"""

#     def __init__(self, context):
#         self.context = context
#         self.doctor_repository = DoctorRepository(self.context.app, AUDIT_TYPE_HOSPITAL)

#     def GetCaseLabExamInfo(self, request, context):
#         response = GetCaseLabExamInfoResponse()
#         app = self.context.getCaseApplication('hospital')
#         if not app:
#             return
#         caseInfo = app.getCaseDetail(request.caseId)
#         if not caseInfo:
#             return
#         firstpageInfo = app.getFirstPageInfo(request.caseId)
#         temperatureInfo = app.getTemperatureInfo(request.caseId)
#         diagnosisInfo = app.getDiagnosisInfo(request.caseId)
#         caseInfo.auditRecord = None
#         result = {i: [] for i in range(1, 5)}
#         witch_data = {
#             1: {
#                 'func': app.getCaseEmr, 'req': GetEmrListRequest,
#                 'reqDict': {'caseId': request.caseId, 'withContent': True, "is_export": 1}
#             },
#             2: {
#                 'func': self.context.getOrderRepository('hospital').search, 'req': GetOrderListRequest,
#                 'reqDict': {'caseId': request.caseId, "is_export": 1}
#             },
#             3: {
#                 'func': app.getCaseAssayList, 'req': GetAssayListRequest,
#                 'reqDict': {'caseId': request.caseId, 'withContent': True, "is_export": 1}
#             },
#             4: {
#                 'func': app.getCaseExamList, 'req': GetExamListRequest,
#                 'reqDict': {'caseId': request.caseId, 'withContent': True, "is_export": 1}
#             }
#         }
#         if request.partOfData:
#             part = witch_data.get(request.partOfData, {})
#             if part:
#                 if request.partOfData == 2:
#                     with app.app.mysqlConnection.session() as session:
#                         part_result = part['func'](session, part['req'](**part['reqDict']))
#                 else:
#                     part_result = part['func'](part['req'](**part['reqDict']))
#                 result[request.partOfData] = part_result
#         else:
#             for i in range(1, 5):
#                 part = witch_data.get(i, {})
#                 if part:
#                     if i == 2:
#                         with app.app.mysqlConnection.session() as session:
#                             part_result = part['func'](session, part['req'](**part['reqDict']))
#                     else:
#                         part_result = part['func'](part['req'](**part['reqDict']))
#                     result[i] = part_result
#         unmarshalCaseLabExamInfo(response, caseInfo, firstpageInfo, temperatureInfo=temperatureInfo,
#                                  diagnosisInfo=diagnosisInfo, emrinfo=result[1], medicalAdvice=result[2],
#                                  assayList=result[3], examList=result[4], part=request.partOfData)
#         return response

#     def GetDoctorCaseList(self, request, context):
#         """
#         查询医生+医生科室全部病历
#         :param request:
#         :param context:
#         :return:
#         """
#         response = GetDoctorCaseListResponse()
#         self.doctor_repository.get_doctor_case_list(request, response)
#         return response

#     def GetLabExamTips(self, caseId):
#         headers = {
#             'Content-Type': 'application/json',
#         }
#         data = {"data": {"case_id": caseId, "all": "否"}}
#         url = self.context.app.cdssAddr + '/cdss/lab_exam'
#         print(datetime.now())
#         response = requests.post(url, headers=headers, json=data).json().get('data', {})
#         print(datetime.now())
#         # result = {"lab": {}, "exam": {}}
#         # exam = response.get('exam', [])
#         # lab = response.get('lab', [])
#         # for item in exam:
#         # 	result['exam'][item["item_id"]] = item["item_msg"]
#         # for item in lab:
#         # 	result['lab'][item["item_id"]] = {'msg': item["item_msg"], 'range': item['item_range']}
#         # result['vital_signs'] = response.get('vital_signs', [])
#         return response

#     def GetPatientPortrait(self, request, context):
#         """
#         获取患者画像
#         :param request:
#         :return:
#         """
#         response = GetPatientPortraitResponse()
#         queryList = []
#         patientID = request.patientID
#         caseID = request.caseID
#         case = self.context.app.mysqlConnection['case']
#         labInfo = self.context.app.mysqlConnection['labInfo']
#         labContent = self.context.app.mysqlConnection['labContent']
#         examInfo = self.context.app.mysqlConnection['examInfo']
#         examContent = self.context.app.mysqlConnection['examContent']
#         examPosition = self.context.app.mysqlConnection['exam_position']
#         if not patientID and not caseID:
#             # context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
#             # context.set_details("GetPatientPortrait: param patientID or caseID is required.")
#             return response
#         queryList.append(case.patientId == patientID)
#         if caseID:
#             queryList.append(case.caseId == caseID)
#         if patientID:
#             queryList.append(case.patientId == patientID)

#         with self.context.app.mysqlConnection.session() as session:
#             ret = session.query(case).filter(*queryList).order_by(case.id.desc()).first()
#             positionDict = {obj.examname: obj.position for obj in session.query(examPosition).all()}
#             if not ret:
#                 return response

#             else:
#                 caseID = ret.caseId
#                 tips = self.GetLabExamTips(caseID)
#                 response.basicInfo.id = ret.patientId
#                 response.basicInfo.name = tips['basicInfo']['name']
#                 response.basicInfo.age = tips['basicInfo']['age']
#                 response.basicInfo.gender = tips['basicInfo']['gender']
#                 response.basicInfo.height = tips['basicInfo']['height']
#                 response.basicInfo.weight = tips['basicInfo']['weight']

#                 response.diseaseInfo.admitDate = tips['diseaseInfo']['admitDate']
#                 response.diseaseInfo.chiefComplaint = tips['diseaseInfo']['chiefComplaint']
#                 response.diseaseInfo.diagnosis.extend(tips['diseaseInfo']['diagnosis'])
#                 response.diseaseInfo.drugAllergy.extend(tips['diseaseInfo']['drugAllergy'])
#                 response.diseaseInfo.operateDate = tips['diseaseInfo']['operateDate']
#                 response.diseaseInfo.operateName = tips['diseaseInfo']['operateName']

#                 labItems = session.query(labInfo, labContent) \
#                     .join(labContent, labInfo.id == labContent.reportId) \
#                     .filter(labInfo.caseId == caseID, labInfo.reportTime != None) \
#                     .order_by(labInfo.testname, labContent.itemname, labInfo.reportTime)
#                 examItems = session.query(examInfo, examContent).join(examContent, examInfo.id == examContent.reportId) \
#                     .filter(examContent.caseId == caseID, examInfo.reportTime != None)
#                 # {"头部检查": {"[头颅,CT平扫]":["result1","result2"],
#                 #                       "[胸部,CT平扫]":["result1","result2"]
#                 #                       }
#                 # }
#                 titles = {}
#                 for examItem in examItems:
#                     # protoItem = response.items.add()
#                     status = False
#                     for i in positionDict.keys():
#                         if i in examItem.examContent.itemname:
#                             status = True
#                             title = positionDict[i]
#                             if title not in titles:
#                                 titles[title] = [
#                                     {"id": examItem.examContent.id, "date": examItem.examInfo.reportTime,
#                                      "key": examItem.examContent.itemname,
#                                      "value": examItem.examContent.result.replace("\r\n", "")}]
#                             else:
#                                 titles[title].append(
#                                     {"id": examItem.examContent.id, "date": examItem.examInfo.reportTime,
#                                      "key": examItem.examContent.itemname,
#                                      "value": examItem.examContent.result.replace("\r\n", "")})
#                     if not status:
#                         if "其他" in titles:
#                             titles["其他"].append({"id": examItem.examContent.id, "date": examItem.examInfo.reportTime,
#                                                  "key": examItem.examContent.itemname,
#                                                  "value": examItem.examContent.result.replace("\r\n", "")})
#                         else:
#                             titles["其他"] = [{"id": examItem.examContent.id, "date": examItem.examInfo.reportTime,
#                                              "key": examItem.examContent.itemname,
#                                              "value": examItem.examContent.result.replace("\r\n", "")}]

#                 for k, v in titles.items():

#                     for s in v:
#                         # TODO 异常提示不正确，洪波数据无法匹配
#                         for i in tips['items']:
#                             if i["type"] == "exam" and str(s['id']) in [a["key"] for a in i["lines"]]:
#                                 for ii in i["lines"]:
#                                     if str(s['id']) == ii["key"]:
#                                         protoItem = None
#                                         for ite in response.items:
#                                             if ite.title == k + '检查':
#                                                 protoItem = ite
#                                         if not protoItem:
#                                             protoItem = response.items.add()
#                                             protoItem.title = k + '检查'
#                                             protoItem.position[k] = k
#                                             protoItem.type = 'exam'
#                                         # protoItem.total = len(v)
#                                         line = protoItem.lines.add()
#                                         line.value = s["value"]
#                                         line.key = s["key"]
#                                         line.date = datetime.strftime(s["date"], '%Y-%m-%d')
#                                         line.resultTip.extend(ii["status"])

#                 # line.date = vital_sign.get('item_date', '')
#                 # sorted(labItems, key=lambda x: x[0].id)
#                 # labGroup = groupby(labItems, key=lambda x: x[0])
#                 history = {}
#                 # {"C-反应蛋白测定(CRP)": {"C反应蛋白":{"unit":"g","lines":[85.4],"status":"0","labCheckRange":"1-2",
#                 #                                   "date":"2021-12-22","id":"123456"},
#                 #                       "C反应蛋白2":{"unit":"mg","lines":[85.4]},
#                 #                       "C反应蛋白3":{"unit":"kg","lines":[85.4]},
#                 #                       }
#                 # }

#                 for labItem in labItems:
#                     if labItem.labInfo.testname in history:
#                         if labItem.labContent.itemname in history[labItem.labInfo.testname]:
#                             history[labItem.labInfo.testname][labItem.labContent.itemname]["lines"].append(
#                                 labItem.labContent.result)
#                             history[labItem.labInfo.testname][labItem.labContent.itemname]["date"].append(
#                                 labItem.labInfo.reportTime)
#                         else:
#                             itemDict = {"unit": labItem.labContent.unit, "lines": [labItem.labContent.result],
#                                         "status": labItem.labContent.abnormalFlag,
#                                         "labCheckRange": labItem.labContent.valrange if labItem.labContent.valrange else "",
#                                         "date": [labItem.labInfo.reportTime], "id": labItem.labContent.id}
#                             history[labItem.labInfo.testname][labItem.labContent.itemname] = itemDict
#                     else:
#                         itemDict = {"unit": labItem.labContent.unit, "lines": [labItem.labContent.result],
#                                     "status": labItem.labContent.abnormalFlag,
#                                     "labCheckRange": labItem.labContent.valrange if labItem.labContent.valrange else "",
#                                     "date": [labItem.labInfo.reportTime], "id": labItem.labContent.id}
#                         history[labItem.labInfo.testname] = {labItem.labContent.itemname: itemDict}
#                 for k, v in history.items():

#                     for sk, sv in v.items():
#                         for s in tips['items']:
#                             if s["type"] == "lab" and str(sv['id']) in [a["key"] for a in s["lines"]]:
#                                 for ii in s["lines"]:
#                                     if str(sv['id']) == ii["key"]:
#                                         protoItem = None
#                                         for ite in response.items:
#                                             if ite.title == k:
#                                                 protoItem = ite
#                                         if not protoItem:
#                                             protoItem = response.items.add()
#                                             protoItem.title = k
#                                             protoItem.type = "lab"
#                                         # protoItem.total = len(v.values())
#                                         line = protoItem.lines.add()  # {"unit":"kg","lines":[85.4]},
#                                         line.key = sk
#                                         line.value = sv["lines"][-1]
#                                         line.status = str(sv["status"]) if sv["status"] else ""
#                                         for i in range(len(sv["lines"])):
#                                             sub = line.trend.add()
#                                             sub.time = datetime.strftime(sv["date"][i], '%Y-%m-%d')
#                                             sub.value = sv["lines"][i]

#                                         line.date = datetime.strftime(sv["date"][-1], '%Y-%m-%d')
#                                         line.unit = sv["unit"] if sv["unit"] else ""
#                                         line.labCheckRange = ii["labCheckRange"] if ii["labCheckRange"] else ""
#                                         line.resultTip.extend(ii["status"])

#                     # if sv["id"] in tips['lab']:
#                     # 	protoItem.resultTip.extend(tips['lab'][sv["id"]]['msg'])
#                     # 	line.labCheckRange = tips['lab'][sv["id"]]['range']

#         for vital_sign in tips["items"]:
#             if vital_sign["type"] == "vs":
#                 protoItem = response.items.add()
#                 protoItem.title = vital_sign["title"]
#                 protoItem.type = "vital_sign"
#                 protoItem.total = vital_sign["total"]
#                 for l in vital_sign["lines"]:
#                     line = protoItem.lines.add()
#                     line.key = l["key"]
#                     line.resultTip.extend(l["status"])
#                     line.value = str(l["value"])
#                     line.date = l["date"]
#                     line.labCheckRange = l["labCheckRange"]
#         for p in response.items:
#             p.total = len(p.lines)

#         return response

#     def getDataFromRedis(self, caseId, redis_pool):
#         with Redis(connection_pool=redis_pool) as redis:
#             key = "casedata_" + caseId
#             data = redis.hgetall(key)
#         return data

#     def GetQcAuditDataByCaseId(self, request, context):
#         response = GetQcAuditDataByCaseIdResponse()
#         start_time = time.time()
#         app = self.context.getCaseApplication('hospital')
#         # 先从redis中查找
#         # redis_pool = app.app.redis_pool
#         # redis_data = self.getDataFromRedis(request.caseId, redis_pool)
#         if not app:
#             return
#         repo = QCCdssRepository(self.context.app)
#         witch_data = {
#             1: repo.getCaseEmr,
#             2: repo.getDoctorAdvice,
#             3: repo.getLabList,
#             4: repo.getExamList,
#             5: repo.getTemperatureInfo,
#             6: repo.getMZDiagnosisInfo,
#             7: repo.getFpDiagnosisInfo,
#             8: repo.getFpOperationInfo,
#             9: repo.getPathologyInfo
#         }
#         # type_selector = {
#         #     1: 'emr',
#         #     2: 'doctor_advice',
#         #     3: 'labs',
#         #     4: 'exams',
#         #     5: 'temperatureInfo',
#         #     6: 'diagnosisInfo',
#         #     7: 'fpDiagnosisInfo',
#         #     8: 'fpOperationInfo',
#         #     9: 'pathologyInfo'
#         # }
#         _unmarshal = "unmarshal"
#         data_dict = {}
#         with self.context.app.mysqlConnection.session() as session:
#             caseInfo = repo.getCaseDetail(session, request.caseId)
#             if not caseInfo:
#                 return
#             firstpageInfo = repo.getFirstPageInfo(session, request.caseId)
#             if request.partOfData:
#                 # dataModified = redis_data.get(type_selector[request.partOfData], {}).get('_dataModified', '')
#                 # reqDict = {'caseId': request.caseId, 'withContent': True, "is_export": 1, 'dataModified': dataModified}
#                 reqDict = {'caseId': request.caseId, 'withContent': True, "is_export": 1}
#                 req = GetAuditInfoBaseRequest(**reqDict)
#                 func = witch_data.get(request.partOfData, None)
#                 if func:
#                     data = func(session, req)
#                     key = _unmarshal + str(request.partOfData)
#                     data_dict[key] = data
#             else:
#                 for index, func in witch_data.items():
#                     # dataModified = redis_data.get(type_selector[index], {}).get('_dataModified', '')
#                     # reqDict = {'caseId': request.caseId, 'withContent': True, "is_export": 1, 'dataModified': dataModified}
#                     reqDict = {'caseId': request.caseId, 'withContent': True, "is_export": 1}
#                     req = GetAuditInfoBaseRequest(**reqDict)
#                     data = func(session, req)
#                     key = _unmarshal + str(index)
#                     data_dict[key] = data
#                     logging.info("caseId = " + req.caseId + ", step: " + str(index))
#                 department_dict = repo.getDepartmentDict(session)
#                 sql_time = time.time() - start_time
#                 logging.info('sql time %s' % sql_time)
#             unmarshal_data_dict = unmarshalQcAuditData(response, **data_dict)
#         QCunmarshalCaseInfo(caseInfo, response.basicInfo, 'hosipital', department_dict)
#         QCunmarshalFirstPageInfo(response.firstPageInfo, firstpageInfo)
#         unmarshal_time = time.time() - sql_time
#         logging.info('unmarshal_time %s' % unmarshal_time)
#         # unmarshal_data_dict['basic_info'] = MessageToDict(response.basicInfo)
#         # unmarshal_data_dict['firstPageInfo'] = MessageToDict(response.firstPageInfo)
#         return response

#     def GetParserResult(self, request, context):
#         response = GetParserResultResponse()
#         app = self.context.getCaseApplication('hospital')
#         result = app.getCaseEmrParserResult(request.caseId)
#         for doc_id, field_list in result.items():
#             protoItem = response.item[doc_id]
#             for field in field_list:
#                 s = Struct()
#                 s.update(field)
#                 protoItem.fields.append(s)
#         return response
