# coding: utf-8

"""用于类型注解的可复用的自定义类型
"""

from typing import List, Tuple, Set, Iterable

StrList = List[str]
StrIterable = Iterable[str]
StrSet = Set[str]
Pair = Tuple[str, str]
StrTuple = Tuple[str]
TupleList = List[Tuple[str, str]]

#: 文书标题, 标准文书英文名称, 正则表达式, 都为字符串
DocTitle = DocType = str

#: 标准文书英文名称列表
DocTypes = List[DocType]
