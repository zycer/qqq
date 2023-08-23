# coding: utf-8

"""特殊对照与特殊正则
"""

import re
from collections import defaultdict
from re import Pattern
from typing import Dict, ClassVar, Optional, List

from pydantic import BaseModel

from .contrast import Contrast
from .types import Pair, StrSet, DocTitle, DocTypes, DocType, StrList


class _BasicModel(BaseModel):
    """允许使用任意类型的 BaseModel"""
    class Config:
        """模型设置为允许任意类型"""
        arbitrary_types_allowed = True


class SpecialRaw(_BasicModel):
    """特殊对照数据源"""

    #: 文书名称到标准文书中文名称的对照
    mapping: List[Pair] = []

    #: 正则到标准文书中文名称的对照
    regs: List[Pair] = []

    #: 医师姓名与职称的对照, 职称 A 对到主任, F 对到主治, 其他忽略
    doctors: List[Pair] = []

    def to_special(self, contrast: Contrast) -> 'Special':
        """转为 :class:`Special`"""
        mapping = defaultdict(list)
        for k, v in self.mapping:
            mapping[k].append(contrast.name_to_full_doc_type[v])

        regs = defaultdict(list)
        for k, v in self.regs:
            regs[re.compile(k)].append(contrast.name_to_full_doc_type[v])

        common_regs = {}
        for k, v in contrast.reg_to_doc_type.items():
            common_regs[re.compile(k)] = v

        return Special(
            mapping=mapping,
            regs=regs,
            common_regs=common_regs,
            doctors_a={name for name, level in self.doctors if level == "A"},
            doctors_f={name for name, level in self.doctors if level == "F"},
        )


class Special(_BasicModel):
    """特殊对照"""
    check_record: ClassVar[str] = "check_record"
    check_record_af: ClassVar[str] = "check_record_superior_physician"
    check_record_a: ClassVar[str] = "check_record_chief_physician"
    check_record_f: ClassVar[str] = "check_record_attending_physician"
    name_pattern: ClassVar[Pattern] = re.compile(
        r"(术前|术后)?(主刀)?(（兼）|\(兼\)|兼)?(医师|医生)?"
        r"(?P<name>.*?)(兼)?"
        r"(术前|主任|主治|首次|主刀|术后|请选择|科副主任|副科主任|科室主任|科室副主任|住院医生|医师|医疗|二级医生|二级医师"
        r"|医生|科主任|副主任|医疗组长|住院医师|院长|副院长|医组长|医师兼医疗组长)"
    )

    #: 文书标题到标准文书英文名称列表的对照, 优先进行匹配
    mapping: Dict[DocTitle, DocTypes] = {}

    #: 本医院自定义正则表达式到标准文书英文名称列表的对照, 优先于通用正则表达式
    regs: Dict[Pattern, DocTypes] = {}

    #: 通用正则表达式到标准文书英文名称列表的对照
    common_regs: Dict[Pattern, DocType] = {}

    #: 主任医师名称集合
    doctors_a: StrSet = set()

    #: 主治医师名称集合
    doctors_f: StrSet = set()

    @classmethod
    def doctor_name_in_title(cls, doc_title: str) -> Optional[str]:
        """提取文书标题中的医生姓名, 提取不到则返回 None"""
        if match := cls.name_pattern.match(doc_title):
            if name := match["name"]:
                return name
        return None

    def doc_types_by_title(self, doc_title: str) -> StrList:
        """根据文书名称返回标准文书英文名称全称列表, 按以下顺序
        1. 含 "作废" 则反馈空列表
        2. 若有特殊对照, 返回特殊对照结果
        3. 若特殊正则匹配成功, 返回匹配结果
        4. 遍历通用正则, 得到匹配结果
        """
        if "作废" in doc_title:
            return []

        if mapped := self.mapping.get(doc_title):
            return mapped

        doc_types = []
        for reg, matched_doc_types in self.regs.items():
            if re.search(reg, doc_title):
                doc_types.extend(matched_doc_types)
        if doc_types:
            return doc_types

        doc_types = [
            doc_type for reg, doc_type in self.common_regs.items()
            if reg.search(doc_title)
        ]
        return doc_types

    def doc_types_about_doctor(self, doc_title: str) -> StrList:
        """根据文书中医生名称判定"""
        doc_types = []
        doctor_name = self.doctor_name_in_title(doc_title)
        if doctor_name is None:
            return doc_types

        if doctor_name in self.doctors_a:
            doc_types.append(self.check_record_a)
        if doctor_name in self.doctors_f:
            doc_types.append(self.check_record_f)
        if doc_types:
            doc_types.insert(0, self.check_record_af)
        return doc_types
