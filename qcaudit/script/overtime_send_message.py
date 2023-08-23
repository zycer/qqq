#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: overtime_send_message.py
@time: 2021/12/7 3:52 下午
@desc: 整改时限的最后一天的下午四点自动发消息
"""
from datetime import datetime, timedelta

import pymysql

import pika
import json
import logging
import time


class RabbitMQ:

    def __init__(self, url):
        self.url = url
        self.connect()

    def connect(self):
        self.connection = pika.BlockingConnection(
            pika.URLParameters(self.url)
        )
        self.channel = self.connection.channel()

    def publish(self, message: dict, exchange='qcaudit', routing_key='socket_queue'):
        """
        发送消息
        :return:
        """
        try:
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key or message['type'],
                body=json.dumps(message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2
                )
            )
        except pika.exceptions.AMQPConnectionError as e:
            logging.exception(e)
            time.sleep(0.1)
            self.connect()
            self.publish(message, exchange, routing_key)


class ConnectMysql:

    def __init__(self, host="localhost", port=3306, user="root", password="rxthinkingmysql", charset="utf8",
                 database="qcmanager"):
        self.db = pymysql.connect(host=host, user=user, password=password, charset=charset,
                                  database=database, port=port)
        self.cursor = self.db.cursor(cursor=pymysql.cursors.DictCursor)
        self.mq = RabbitMQ("amqp://rxthinking:gniknihtxr@192.168.100.40:42158/%2F")  # 开发环境 todo 改线上地址
        # self.mq = RabbitMQ("amqp://rxthinking:gniknihtxr@192.168.101.185:31232/%2F")  # 测试环境

    def run_server(self):
        """
        启动服务
        :return:
        """
        print("start runserver", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        today_fix_deadline = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        query_refuse_history_sql = '''select patient_id, caseId, problems from refuse_history where fix_deadline = "%s"''' % today_fix_deadline
        print("query_refuse_history_sql:", query_refuse_history_sql)
        self.cursor.execute(query_refuse_history_sql)
        refuse_history_data = self.cursor.fetchall()
        if not refuse_history_data:
            print("no refuse_history_data")
            return
        for item in refuse_history_data:
            send_user_list = []  # 保证同一条消息只发送给一个用户
            caseId = item["caseId"]
            patientId = item["patient_id"]
            problems = json.loads(item["problems"]) if item["problems"] else []
            problem_ids = ",".join([str(problem["problemId"]) for problem in problems])
            query_problem_sql = '''select distinct doctorCode from caseProblem where caseId = "%s" and id in (%s) and is_fix = 0 and is_ignore = 0''' % (caseId, problem_ids)
            self.cursor.execute(query_problem_sql)
            problem_data = self.cursor.fetchall()
            if not problem_data:
                print("problem is fixed or ignore")
                continue
            query_case_sql = '''select name, attendCode from `case` where caseId = "%s"''' % caseId
            print("query_case_sql:", query_case_sql)
            self.cursor.execute(query_case_sql)
            case_info = self.cursor.fetchone()
            print("case_info:", case_info)
            name = case_info["name"]
            attendCode = case_info["attendCode"]
            for item1 in problem_data:
                receive_user = item1["doctorCode"] or attendCode
                if receive_user in send_user_list:
                    continue
                msg = "【{name}】病历即将超过整改时限，请尽快处理。".format(name=name)
                message = {
                    'caseId': caseId,
                    'send_user': 'system',
                    'message': msg,
                    'receive_user': str(receive_user),
                    'tupType': 1,
                    'send_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': '病历质控提醒',
                    "project": "病历质控",
                }
                self.mq.publish(message)
                print("send success message:", message)
                send_user_list.append(receive_user)


if __name__ == '__main__':
    tmp = ConnectMysql(host="192.168.101.186", port=31444, database="qcmanager_v3")
    tmp.run_server()
