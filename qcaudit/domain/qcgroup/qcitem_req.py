#!/usr/bin/env python3


from dataclasses import dataclass, field
from typing import List

from sqlalchemy import text, or_

from qcaudit.domain.req import ListRequestBase


@dataclass
class GetItemsListRequest(ListRequestBase):
    id: int = 0
    code: str = ''
    requirement: str = ''
    instruction: int = 0
    emrName: int = 0
    type: int = 0  # 质控类别 1通用，2专科，3专病
    department: str = ''
    disease: str = ''
    status: int = 0  # 是否确认 1 未确认，2已确认
    custom: int = 0  # 人工or机器 1=人工，2=机器
    enable: int = 0  # 启用状态 1=停用 2=启用
    enableType: int = 0  # 质控状态 1=质控问题 2=提示问题
    tag: int = 0  # 标记 0-全部，1-强制，2-否决
    # 默认情况下获取全部
    size: int = 10000
    start: int = 0
    ids: List[int] = field(default_factory=list)
    caseId: str = ""
    # 专病筛选
    diagnosis: List[str] = field(default_factory=list)
    # 专科筛选
    dept: str = ""
    # 规则类型, 时效性=1，一致性=2，完整性=3，正确性=4, 全部-0
    category: int = 0

    def applyFilter(self, query, connection):
        itemModel = connection['qcItem']

        # 指定id忽略其他条件
        if self.id:
            query = query.filter(itemModel.id == self.id)
            return query

        if self.code:
            query = query.filter(itemModel.code == self.code)
        if self.requirement:
            query = self.applyLikeFilter(query, 'requirement', self.requirement, itemModel)
        if self.instruction:
            like_str = '%' + '%'.join([_ for _ in self.instruction]) + '%'
            query = query.filter(itemModel.instruction.like(like_str))
        if self.emrName:
            query = query.filter(itemModel.standard_emr == self.emrName)
        if self.type:
            query = query.filter(itemModel.type == self.type)
        if self.department:
            query = self.applyLikeFilter(query, 'departments', self.department, itemModel)
        if self.disease:
            query = self.applyLikeFilter(query, 'disease', self.disease, itemModel)
        if self.status:
            query = query.filter(itemModel.approve_status == self.status)
        if self.custom:
            if self.custom == 1:
                query = query.filter(itemModel.custom == 1)
            elif self.custom == 2:
                query = query.filter(itemModel.custom == 0)
        if self.enable:
            query = query.filter(itemModel.enable == self.enable)
        if self.caseId:
            # 存在caseId说明是质控页面查询质控点, 仅查看未停用的
            query = query.filter(itemModel.enable == 2)
        if self.ids:
            query = query.filter(itemModel.id.in_(self.ids))
        if self.tag:
            query = query.filter(itemModel.veto == self.tag)
        if self.category:
            query = query.filter(itemModel.category == self.category)
        if self.enableType:
            query = query.filter(itemModel.enableType == self.enableType)
        if self.diagnosis or self.dept:
            _or = or_()
            for diag in self.diagnosis:
                _or.append(itemModel.disease.like('%%%s%%' % diag))
            _or.append(itemModel.departments.like('%%%s%%' % self.dept))
            _or.append(itemModel.type == 1)
            query = query.filter(_or)
        # 从未删除的质控点中查询
        query = query.filter(itemModel.is_deleted == 0).order_by(itemModel.id.desc())
        return query
