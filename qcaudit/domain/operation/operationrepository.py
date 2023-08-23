#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   operationrepository.py
@Time    :   2023/06/27 10:22:03
@Author  :   zhangda 
@Desc    :   None
'''


import arrow

from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.operation.operation import Operation, CodingOperation, OperationDict
from qcaudit.domain.operation.req import OperationRequest
from sqlalchemy.orm import aliased
from sqlalchemy import func
from qcaudit.common.const import OPERATION_CUT_LEVEL, OPERATION_HEAL_LEVEL, OPERATION_LEVEL


class OperationRepository(RepositoryBase):
	def __init__(self, app):
		super().__init__(app)
		self.operation = app.mysqlConnection['operation']
		self.operation_info = app.mysqlConnection['operation_info']
		self.operation_dict = app.mysqlConnection['mi_operation_dict']
		self.operation_origin_dict = app.mysqlConnection['operation_origin_dict']
		self.doctor = app.mysqlConnection['doctor']

	def initOperationList(self, session, caseId):
		operationObjs = session.query(self.operation, self.operation_dict) \
			.outerjoin(self.operation_dict, self.operation_dict.name == self.operation.oper_name) \
			.filter(self.operation.caseId == caseId) \
			.all()
		self.deleteOperation(session, caseId)
		for obj in operationObjs:
			orderNum = 1
			obj = Operation(obj[0], obj[1])
			item = self.operation_info(
				caseId=obj.model.caseId,
				code=obj.operationDict.code if obj.operationDict else '',
				originName=obj.model.oper_name,
				name=obj.operationDict.name if obj.operationDict else '',
				type=obj.operationDict.type if obj.operationDict else '',
				operation_time=obj.model.oper_date,
				level=self.findOperationLevel(obj.model.oper_level),
				operator=obj.model.oper_doctor,
				helperOne=obj.model.assistant_1,
				helperTwo=obj.model.assistant_2,
				cut=self.findOperationCutLevel(obj.model.cut_level),
				healLevel=self.findOperationHealLevel(obj.model.heal_level),
				narcosis=obj.model.ane_method,
				narcosisDoctor=obj.model.ans_doctor,
				create_time=arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
				update_time=arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
				orderNum=orderNum
			)
			session.add(item)
			orderNum += 1

	def deleteOperation(self, session, caseId):
		objs = session.query(self.operation_info).filter(self.operation_info.caseId == caseId).all()
		if objs:
			for obj in objs:
				obj.is_deleted = 1
			session.commit()

	def getOperationList(self, session, caseId):
		result = []
		operator = aliased(self.doctor)
		helperOne = aliased(self.doctor)
		helperTwo = aliased(self.doctor)
		narcosisDoctor = aliased(self.doctor)
		operationObjs = session.query(
			self.operation_info,
			operator.name.label('operator'),
			helperOne.name.label('helperOne'),
			helperTwo.name.label('helperTwo'),
			narcosisDoctor.name.label('narcosisDoctor'),
		).outerjoin(
			operator, self.operation_info.operator == operator.id
		).outerjoin(
			helperOne, self.operation_info.helperOne == helperOne.id
		).outerjoin(
			helperTwo, self.operation_info.helperTwo == helperTwo.id
		).outerjoin(
			narcosisDoctor, self.operation_info.narcosisDoctor == narcosisDoctor.id
		).filter(
			self.operation_info.caseId == caseId,
			self.operation_info.is_deleted == 0
		).order_by(self.operation_info.orderNum).all()
		for obj in operationObjs:
			result.append(
				CodingOperation(obj[0], operator=obj[1], helperOne=obj[2], helperTwo=obj[3], narcosisDoctor=obj[4])
			)
		return result

	def updateOperation(self, session, caseId, id, updateDict):
		if not id:
			"""新增数据"""
			max_orderNum=session.query(func.max(self.operation_info.orderNum)).filter(self.operation_info.caseId==caseId,self.operation_info.is_deleted==0).first()[0]
			if max_orderNum:
				orderNum = max_orderNum + 1
			else:
				orderNum = 1
			operObj = self.operation_info(
				**updateDict,
				caseId=caseId,
				orderNum=orderNum,
				create_time=arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
				update_time=arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
			)
			session.add(operObj)
			session.commit()
			return operObj
		operObj = session.query(self.operation_info) \
			.filter(
			self.operation_info.caseId == caseId,
			self.operation_info.id == id) \
			.first()
		oper = Operation(operObj)
		oper.setModel(
			**updateDict,
			update_time=arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
		)
		session.add(operObj)
		session.commit()
		return operObj

	def updateOperationOriginDict(self, session, operation_info):
		originName = operation_info.originName
		newName = operation_info.name
		originDict = session.query(self.operation_origin_dict).filter(self.operation_origin_dict.originName == originName).first()
		newDict = session.query(self.operation_dict).filter(self.operation_dict.name == newName).first()
		if not newDict:
			return
		if originDict and originDict.name == newName:
			return
		if originDict:
			originDict.code = newDict.code
			originDict.name = newDict.name
			originDict.type = newDict.type
		else:
			item = self.operation_origin_dict(
				code=newDict.code,
				type=newDict.type,
				name=newName,
				originName=originName,
				create_time=arrow.utcnow().to("+08:00").naive.strftime('%Y-%m-%d %H:%M:%S')
			)
			session.add(item)

	def getOperationFromDict(self, session, req: OperationRequest):
		data = []
		if originName := req.originName:
			originOperQuery = session.query(self.operation_origin_dict).filter(self.operation_origin_dict.originName == originName).first()
			if originOperQuery and originOperQuery.name != originName:
				data.append(Operation(originOperQuery))
			data.extend(self.query_operation_by_originName(originName, req))
			return data
		query = session.query(self.operation_dict)
		query = req.applyFilter(query, self.app.mysqlConnection)
		for item in query.limit(20).all():
			data.append(Operation(item))
		return data

	def getOriginOperationList(self, session, caseId):
		result = []
		query = session.query(self.operation).filter(self.operation.caseId == caseId)
		query_used = session.query(self.operation_info.originName).filter(
			self.operation_info.caseId == caseId, self.operation_info.is_deleted == 0).all()
		used_list = [item.originName for item in query_used]  # 已使用展示的原始手术, 不需要在次展示使用
		for item in query.all():
			if item.oper_name not in used_list:
				result.append(Operation(item))
		return result

	def updateOperationOrderNum(self, session, sortIds):
		for index in range(len(sortIds)):
			session.query(self.operation_info).filter(
				self.operation_info.id == sortIds[index]).update({'orderNum': index + 1}, synchronize_session=False)

	def findOperationCutLevel(self, origin):
		for key, value in OPERATION_CUT_LEVEL.items():
			if origin and origin in value:
				return key
		return None

	def findOperationHealLevel(self, origin):
		for key in OPERATION_HEAL_LEVEL:
			if origin and key in origin:
				return key
		return None

	def findOperationLevel(self, origin):
		for key, value in OPERATION_LEVEL.items():
			if origin and origin in value:
				return key
		return None

	def query_count_by_caseId(self, session, caseId):
		"""
		查询无条件手术数据
		:return:
		"""
		query_count = session.query(func.count(self.operation_info.id).label("c")).filter(
			self.operation_info.caseId == caseId).first()
		return query_count.c

	def query_operation_by_originName(self, originName, req):
		"""
		查询命中最高的手术
		:return:
		"""
		base_dict = req.base_dict
		name_code_dict = req.name_code_dict
		name_type_dict = req.name_type_dict
		all_list = []
		for word in originName:
			all_list.extend(base_dict.get(word, []))
		operation_count_dict = {}
		for item in all_list:
			if not operation_count_dict.get(item, 0):
				operation_count_dict[item] = 0
			operation_count_dict[item] += 1
		sort_operation_list = sorted(operation_count_dict, key=lambda key: operation_count_dict[key], reverse=True)
		obj1 = None
		if name_code_dict.get(originName, ""):
			obj1 = OperationDict.newObject(self.app)
			obj1.setModel(code=name_code_dict[originName], name=originName, type=name_type_dict[originName])
		res = []
		if obj1:
			res.append(obj1)
		for name in sort_operation_list[:21]:
			if name_code_dict.get(name, "") and name != originName:
				obj = OperationDict.newObject(self.app)
				obj.setModel(code=name_code_dict[name], name=name, type=name_type_dict[name])
				res.append(obj)
		return res
