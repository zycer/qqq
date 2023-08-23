# coding: utf-8

"""标准文书层级, 中英文名称与正则
"""
import csv
from typing import Dict, Iterable

from pydantic import BaseModel

from .types import StrSet, StrList


class DocTypeItem(BaseModel):
    """标准文书对照每项
    """

    #: 标准文书中文名称
    name: str

    #: 标准文书英文名称, 含 $ 分隔符的完整路径
    type: str

    #: 正则表达式
    reg: str = ""

    #: 是否为单文书
    is_singleton: bool = False

    #: 是否调用模型
    has_models: bool = False

    @property
    def accurate_doc_type(self) -> str:
        """精确子级英文名称"""
        return self.type.rsplit("$", maxsplit=1)[-1]


class Contrast(BaseModel):
    """对照类"""

    #: 标准文书中文名称与英文名称的字典, 含 $ 分隔符
    name_to_full_doc_type: Dict[str, str] = {}

    #: 标准文书英文名称与中文名称的字典, 含 $ 分隔符
    full_doc_type_to_name: Dict[str, str] = {}

    #: 标准文书英文名称与中文名称的字典, 不含 $ 分隔符
    accurate_doc_type_to_name: Dict[str, str] = {}

    #: 每项为正则表达式与标准文书英文名称(含 $ 分隔符)二元组的列表
    reg_to_doc_type: Dict[str, str] = {}

    #: 单文书的标准文书英文名称, 不含 $
    singleton_doc_types: StrSet = set()

    #: 使用模型的标准文书英文名称, 不含 $
    has_models_doc_types: StrSet = set()

    @classmethod
    def from_doc_type_items(cls, doc_type_items: Iterable[DocTypeItem]):
        """从 DocTypeItem 迭代器构建"""
        self = cls()
        for item in doc_type_items:
            self.name_to_full_doc_type[item.name] = item.type
            self.full_doc_type_to_name[item.type] = item.name
            self.accurate_doc_type_to_name[item.accurate_doc_type] = item.name
            self.reg_to_doc_type[item.reg] = item.type
            if item.is_singleton:
                self.singleton_doc_types.add(item.accurate_doc_type)
            if item.has_models:
                self.has_models_doc_types.add(item.accurate_doc_type)
        return self

    @classmethod
    def from_csv(cls, path: str):
        """从 csv 文件加载"""
        with open(path) as f:
            reader = csv.DictReader(f)
            doc_type_items = (DocTypeItem.parse_obj(line) for line in reader)
            self = cls.from_doc_type_items(doc_type_items)
            return self

    @classmethod
    def all_doc_types(cls, doc_types: StrList) -> StrList:
        """doc_types 的格式为 ['$a$b', '$c'], 转为 ['a', 'b', 'c']"""
        rv = []
        for item in doc_types:
            for node in item[1:].split("$"):
                if node not in rv:
                    rv.append(node)
        return rv

    @classmethod
    def accurate_doc_types_set(cls, doc_types: StrList) -> StrSet:
        """doc_types 的格式为 ['$a$b', '$c'], 转为 {'b', 'c'}"""
        rv = {doc_type.rsplit("$", maxsplit=1)[-1] for doc_type in doc_types}
        return rv

    def en_doc_types_to_cn(self, doc_types: StrList) -> StrList:
        """将标准文书英文名称列表转为标准文书中文名称列表"""
        return [self.accurate_doc_type_to_name[doc_type] for doc_type in doc_types]

    def cn_doc_types_to_en(self, cn_doc_types: StrList) -> StrList:
        """将标准文书中文名称列表转为标准文书英文名称列表"""
        return [self.name_to_full_doc_type[doc_type] for doc_type in cn_doc_types]

    def sub_names_by_name(self, name: str) -> StrSet:
        """根据标准文书中文名称获取自身及所有子级文书中文名称集合"""
        doc_type = self.name_to_full_doc_type[name]
        names = {name for full_doc_type, name in self.full_doc_type_to_name.items()
                 if full_doc_type.startswith(doc_type)}
        return names

    def all_names_by_names(self, names: StrSet) -> StrList:
        """返回给定文书名称集合及每项子类的集合
        用于事中标准文书推断后的子类型拓展.
        """
        rv = set()
        for name in names:
            rv |= self.sub_names_by_name(name)
        return sorted(rv)

    def parser_names(self, cn_doc_types: StrList):
        """找到给定的标准文书中文名称列表中的最精确子集列表, 转为精确英文名称作为解析器名称"""
        en_doc_types = self.cn_doc_types_to_en(cn_doc_types)
        rv = [
            doc_type.rsplit("$", maxsplit=1)[-1] for doc_type in en_doc_types
            if not any(
                item for item in en_doc_types
                if item != doc_type and item.startswith(doc_type)
            )
        ]
        return rv
