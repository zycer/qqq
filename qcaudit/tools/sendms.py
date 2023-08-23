#!/usr/bin/env python3
# coding=utf-8
'''
Author: qiupengfei@rxthinking.com
Date: 2021-01-15 12:55:28

'''
import sys
from argparse import ArgumentParser
import json
import pika
import logging
import platform

PYTHON_VERSION = platform.python_version()
is_python3 = PYTHON_VERSION.startswith('3')

if not is_python3:
    reload(sys)
    sys.setdefaultencoding('utf-8')


class Rabbitmq(object):

    def __init__(self, url):
        self.connection = pika.BlockingConnection(
            pika.URLParameters(url)
        )
        self.channel = self.connection.channel()

    def publish(self, message, exchange='qcetl'):
        self.channel.basic_publish(exchange=exchange,
                                   routing_key=message['type'],
                                   body=json.dumps(message, ensure_ascii=False),
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,  # make message persistent
                                   ))

    def iterQueue(self, queue):
        """clear and return all the messages"""
        while True:
            method_frame, header_frame, body = self.channel.basic_get(queue)

            if method_frame:
                self.channel.basic_ack(method_frame.delivery_tag)
                yield json.loads(body)
            else:
                break

    def file2queue(self, filename, exchange):
        count = 0
        if filename:
            df = open(filename)
        else:
            df = sys.stdin
        for line in df:
            if not line.strip():
                continue
            message = json.loads(line)
            self.publish(message)
            count += 1
        if filename:
            df.close()
        logging.info('%d records sent to mq', count)

    def queue2file(self, queue, filename):
        if filename:
            df = open(filename, 'w')
        else:
            df = sys.stdout
        for message in self.iterQueue(queue):
            df.write('%s\n' % json.dumps(message, ensure_ascii=False))
        if filename:
            df.close()

    def close(self):
        self.connection.close()


f2q_desc = '''
### 从文件加载消息发送到队列

文件中每一行是一条消息的内容，格式JSON类型，需要包含type和body字段

### 例子：
```json
{"body": {"caseId": "866659", "patientId": "564321"}, "type":"qc.archive"}
{"body": {"caseId": "865177", "docId": "1234567890"}, "type":"emr.doc.save"}
```

'''

q2f_desc = '''
### 导出队列中的消息到文件
'''

pub_desc = '''
### 自定义消息内容

发送单个消息，需要指定type和body

### 消息类型
- qc.archive 申请归档
- emr.doc.save 保存文书
- qc.ai.archive 运行ai质控

body 用逗号分隔 例子：caseId=7948899,patientId=123456,docId=123123
'''


def getArgs():
    parser = ArgumentParser(prog='发送指定消息', description='### 发送指定消息到队列')
    parser.add_argument('--mq-url', dest='mqUrl', default='amqp://rxthinking:gniknihtxr@127.0.0.1:42158/%2F',
                        help='rabbitmq amqp url, Default: %(default)s')
    parser.add_argument('--exchange', default='qcetl', help='Exchange, Default: %(default)s')

    sub_parsers = parser.add_subparsers(dest='action')

    f2q_parser = sub_parsers.add_parser('f2q', help='sent file to queue', description=f2q_desc)
    f2q_parser.add_argument('-f', dest='filename', required=True, help='default from stdin')

    q2f_parser = sub_parsers.add_parser('q2f', help='read queue to file', description=q2f_desc)
    q2f_parser.add_argument('-f', dest='filename', help='Default to stdout')
    q2f_parser.add_argument('-q', '--queue', dest='queue')

    pub_parser = sub_parsers.add_parser('pub', help='publish msg to queue through cmdline', description=pub_desc)
    pub_parser.add_argument('--type', dest='type', required=True, help='Message type(routing_key)')
    pub_parser.add_argument('--body', dest='body', required=True, help='patientId=xxx,caseId=xxx')

    return parser


def process(args):
    r = Rabbitmq(args.mqUrl)
    if args.action == 'f2q':
        r.file2queue(args.filename, args.exchange)
    elif args.action == 'q2f':
        r.queue2file(args.queue, args.filename)
    elif args.action == 'pub':
        message = {'type': args.type,
                   'body': {it[0]: it[1] for it in [tuple(item.split('=')) for item in args.body.split(',')]}}
        r.publish(message, args.exchange)
    r.close()


# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getArgs()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process
