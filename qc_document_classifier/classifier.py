# coding: utf-8

"""标准文书对照工具
"""

from typing import List

from .contrast import DocTypeItem, Contrast
from .special import Special, SpecialRaw
from .types import StrList

_empty_special = Special()


class Classifier:
    """管理标准文书层级与对照

    标准文书的英文名称会按级别从粗到细用 self.sep 分隔,
    如 `转入记录` 会对照为 `course_record$transferred_record$transferred_in_record`
    即病程记录下的转科记录的转入记录.
    """

    def __init__(self, doc_type_items: List[DocTypeItem], special_raw: SpecialRaw = None):
        self.contrast: Contrast = Contrast.from_doc_type_items(doc_type_items)
        self.special: Special = _empty_special
        if special_raw:
            self.special = special_raw.to_special(self.contrast)

    def reload_special(self, special_raw: SpecialRaw):
        """重新加载 special"""
        self.special = special_raw.to_special(self.contrast)

    def doc_types_by_title(self, doc_title: str) -> StrList:
        """根据文书名称返回标准文书英文名称列表, 按以下顺序
        1. 根据标题依次使用特殊对照, 特殊正则, 普适正则进行匹配, 匹配到就返回
        2. 若匹配到查房记录, 提取名称匹配更精细的子级
        返回匹配结果, 包括所有父级和子级
        """
        doc_types = self.special.doc_types_by_title(doc_title)
        all_doc_types = self.contrast.all_doc_types(doc_types)

        if Special.check_record in all_doc_types:
            added = self.special.doc_types_about_doctor(doc_title)
            for item in added:
                if item not in all_doc_types:
                    all_doc_types.extend(added)
        return all_doc_types

    def cn_doc_types_by_title(self, doc_title: str) -> StrList:
        """将 :meth:`doc_types_by_title` 的结果转为中文"""
        doc_types = self.doc_types_by_title(doc_title)
        rv = self.contrast.en_doc_types_to_cn(doc_types)
        return rv
