#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   diagnosis_application.py
@Time    :   2023/06/27 10:28:58
@Author  :   zhangda 
@Desc    :   None
'''


import logging
import time


class DiagnosisApplication:

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.diagnosis_dict_model = self.app.mysqlConnection["mi_diagnosis_dict"]
        self.base_dict, self.name_code_dict = self.init_base_dict()

    def init_base_dict(self):
        """
        初始化基础诊断字典
        :return:
        """
        base_dict = {}
        name_code_dict = {}
        start_time = time.time()
        with self.app.mysqlConnection.session() as session:
            query = session.query(self.diagnosis_dict_model)
            for item in query.all():
                name_code_dict[item.name] = item.code
                for word in item.name:
                    if not base_dict.get(word, []):
                        base_dict[word] = []
                    base_dict[word].append(item.name)
        use_time = time.time() - start_time
        self.logger.info("DiagnosisApplication.init_base_dict, use time: %ss, len base_dict: %s", int(use_time), len(base_dict))
        return base_dict, name_code_dict
