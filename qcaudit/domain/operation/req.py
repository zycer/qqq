from dataclasses import dataclass, field
from qcaudit.domain.req import ListRequestBase
from typing import List
from sqlalchemy import or_


@dataclass
class OperationRequest(ListRequestBase):
	# 输入
	input: str = ''
	# 原始手术名称
	originName: List[str] = field(default_factory=list)
	# 基础字典表
	base_dict: dict = field(default=dict)
	# 名称 编码映射表
	name_code_dict: dict = field(default=dict)
	# 名称 类型映射表
	name_type_dict: dict = field(default=dict)

	def applyFilter(self, query, connection):
		model = connection['mi_operation_dict']
		if self.input:
			query_str = "%" + self.input + "%"
			query = query.filter(or_(model.name.like(query_str), model.code.like(query_str), model.initials.like(query_str)))
		return query
