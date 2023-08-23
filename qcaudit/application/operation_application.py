#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: operation_application.py
@time: 2022/2/16 10:08
@desc:
"""
import logging
import time


class OperationApplication:

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.operation_dict_model = self.app.mysqlConnection["mi_operation_dict"]
        self.base_dict, self.name_code_dict, self.name_type_dict = self.init_base_dict()

    def init_base_dict(self):
        """
        初始化基础手术字典
        :return:
        """
        base_dict = {}
        name_code_dict = {}
        name_type_dict = {}
        start_time = time.time()
        with self.app.mysqlConnection.session() as session:
            query = session.query(self.operation_dict_model)
            for item in query.all():
                name_code_dict[item.name] = item.code
                name_type_dict[item.name] = item.type
                for word in item.name:
                    if not base_dict.get(word, []):
                        base_dict[word] = []
                    base_dict[word].append(item.name)
        use_time = time.time() - start_time
        self.logger.info("OperationApplication.init_base_dict, use time: %ss, len base_dict: %s", int(use_time), len(base_dict))
        return base_dict, name_code_dict, name_type_dict
