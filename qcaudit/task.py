#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: task.py
@time: 2022/12/21 17:36
@desc:
"""
import logging
import time

from qcaudit.application.sampleapplication import HospitalSampleApplication


class TaskServer:

    def __init__(self, app):
        self.app = app

    def runTask(self):
        """
        抽取定时任务
        :return:
        """
        sample_app = HospitalSampleApplication(self.app)
        while True:
            task_list = sample_app.queryRunTask()
            if task_list:
                logging.info("to run %s task.", len(task_list))
                for task in task_list:
                    sample_app.run_task(task)
            time.sleep(600)
