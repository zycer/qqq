#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: ruleapplication.py
@time: 2022/4/19 17:10
@desc:
"""
import re

from qcaudit.app import Application
from qcaudit.application.applicationbase import ApplicationBase
from brainmapanalyzer.keywords import Keyword as KeywordBase


class RuleApplication(ApplicationBase):

    def __init__(self, app: Application, auditType: str="hospital"):
        super().__init__(app, auditType)
        self.keywords_data = {}
        self.init_keyword_data()

    def init_keyword_data(self):
        """
        初始化所有脑图查询数据到内存中
        :return:
        """
        keywords_model = self.app.mysqlConnection["qc_keywords"]
        with self.app.mysqlConnection.session() as session:
            query = session.query(keywords_model)
            keyword_list = KeywordBase.fromModels(query.all(), groupSameTable=True, ignoreGroupTables=["case", "firstpage", "_disease_report", "emrInfo"])
            for item in keyword_list:
                self.keywords_data[item.fieldName] = item

    def queryKeywordsData(self, request):
        """
        关键字查询脑图展示数据
        :param request:
        :return:
        """
        data = []
        start = request.start or 0
        size = request.size or 10
        if request.text:
            for name, item in self.keywords_data.items():
                pattern = '.*'.join(request.text)
                regex = re.compile(pattern)
                if regex.search(name):
                    data.append(item)
        elif request.type:
            for name, item in self.keywords_data.items():
                if request.type == item.type:
                    data.append(item)
        res = data
        if len(data) >= start + size:
            res = data[start: start + size]
        elif len(data) > start:
            res = data[start: len(data)]
        # res = [item.asProto() for item in res]
        return res, len(data)

    def queryKeywordsTypesData(self):
        """
        查询脑图数据分类
        :return:
        """
        data = []
        for name, item in self.keywords_data.items():
            if item.type not in data:
                data.append(item.type)
        return data

    def queryKeywordsTypesStatsData(self, request):
        """
        根据关键字查询 存在该关键字的 分类
        :param request:
        :return:
        """
        type_count_dict = {}
        total = 0
        for name, item in self.keywords_data.items():
            pattern = '.*'.join(request.text)
            regex = re.compile(pattern)
            if regex.search(name):
                total += 1
                if not type_count_dict.get(item.type, 0):
                    type_count_dict[item.type] = 0
                type_count_dict[item.type] += 1
        return type_count_dict, total
