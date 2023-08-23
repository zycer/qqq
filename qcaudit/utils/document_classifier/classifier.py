#!/usr/bin/env python3
"""
文书名称对照到标准文书名称
"""
import logging
from typing import ClassVar

from qc_document_classifier.special import SpecialRaw, Special
from qc_document_classifier.classifier import Classifier as _Classifier


class Classifier(_Classifier):

    def doc_types_about_doctor(self, title):
        """根据文书中医生名称判定"""

        check_record_af: ClassVar[str] = "$course_record$check_record$check_record_superior_physician"
        check_record_a: ClassVar[str] = "$course_record$check_record$check_record_superior_physician$check_record_chief_physician"
        check_record_f: ClassVar[str] = "$course_record$check_record$check_record_superior_physician$check_record_attending_physician"

        doc_types = []
        doctor_name = self.special.doctor_name_in_title(title)
        if doctor_name is None:
            return doc_types

        if doctor_name in self.special.doctors_a:
            doc_types.append(check_record_a)
        if doctor_name in self.special.doctors_f:
            doc_types.append(check_record_f)
        if doc_types:
            doc_types.insert(0, check_record_af)
        return doc_types

    def get_full_types_by_title(self, title):
        """
        根据文书名称获取带层级关系的文书类型列表
        1. 根据标题正则匹配查找标准文书类型
        2. 根据医生列表增加文书类型
        3. 文书类型结果按照长度倒序排列，只保留最全的类型列表，转成中文名称
        """
        result = []
        doc_types = self.special.doc_types_by_title(title)

        all_types = self.contrast.all_doc_types(doc_types)
        if Special.check_record in all_types:
            added = self.doc_types_about_doctor(title)
            for item in added:
                if item not in doc_types:
                    doc_types.append(item)
        # 按照文书对照名称倒序排序
        sorted_types = sorted(doc_types, key=lambda data: len(data), reverse=True)

        counter = {}
        for item_type in sorted_types:
            sub_types = self.contrast.all_doc_types([item_type])
            new_flag = False
            for item in sub_types:
                if counter.get(item) is None:
                    new_flag = True
                    counter[item] = 1
            if new_flag:
                result.append('$'.join(self.contrast.en_doc_types_to_cn(sub_types)))
        return result
