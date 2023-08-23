#!/usr/bin/env python3
# coding=utf-8
'''
Author: qiupengfei@rxthinking.com
Date: 2021-01-15 12:55:28

'''
from typing import Iterable
from rabbitmqlib.rabbitmqlib import RabbitMqManager, Message, MessageResult
from argparse import ArgumentParser
import json
import logging
import sys
from collections import deque


class Queue2File:

    def __init__(self, fileHandler):
        self.file = fileHandler

    def onMessage(self, message: Message):
        try:
            self.file.write('%s\n', message.Body)
            return MessageResult(True)
        except Exception as e:
            raise e


def iterQueue(manager: RabbitMqManager, queue) -> Iterable[Message]:
    """遍历rabbitmq中一个队列的消息, 
        这是一个trick, 因为rabbitmqManager必须要求同时指定routingKey等, 而当前需求是获取一个queue, 不需要知道queue的绑定关系

    Args:
        manager (RabbitMqManager): _description_
        queue (str): 要监听的队列名称

    Returns:
        Iterable[Message]: 队列中所有消息的迭代器
    """
    while True:
        # 这是一个trick, 因为rabbitmqManager必须要求同时指定routingKey等, 而当前需求是获取一个queue, 不需要知道queue的绑定关系
        delivery, properties, body = manager._producer.channel.basic_get(queue)
        if delivery:
            manager._producer.channel.basic_ack(delivery.delivery_tag)
            msg = Message(body, manager._producer.channel,
                          deliver=delivery, properties=properties)
            yield msg
        else:
            # 获取不到数据, 队列已经为空
            break


def getArgs():
    parser = ArgumentParser(prog='消息收发工具')
    parser.add_argument('--url', dest='mqUrl', default='amqp://rxthinking:gniknihtxr@rabbitmq.infra-default:5672/%2F',
                        help='rabbitmq amqp url, Default: %(default)s')
    parser.add_argument('--exchange', default='qcetl',
                        help='Exchange, Default: %(default)s')

    subparsers = parser.add_subparsers(dest='action')
    f2q_parser = subparsers.add_parser('f2q', help='发送文件到mq')
    f2q_parser.add_argument('-f', dest='file', type=open, help='要发送的消息文件, 每行一个json, 内容是消息体')
    f2q_parser.add_argument(
        '--routing-key', dest='routingKey', help='Routing Key, 优先取文件json中的type')
    f2q_parser.add_argument(
        '--nobody', help='消息体不放到body中', action='store_true')

    q2f_parser = subparsers.add_parser('q2f', help='读取mq消息写入文件')
    q2f_parser.add_argument('-f', dest='filename', help='输出文件名称')
    q2f_parser.add_argument('-q', '--queue', default='队列名称')

    pub_parser = subparsers.add_parser(
        'pub', help='发送一条消息到rabbitmq')
    pub_parser.add_argument('--routing-key', dest='routingKey',
                            required=True, help='Routing Key')
    pub_parser.add_argument('--body', help='支持json或者kv形式(Example: patientId=xxx,caseId=xxx)')
    pub_parser.add_argument(
        '--nobody', help='消息体不放到body中', action='store_true')
    return parser.parse_args()


def main():
    args = getArgs()
    manager = RabbitMqManager(args.mqUrl)
    # 将文件数据写入到mq
    # 若不指定routingKey, 则使用json的type字段
    if args.action == 'f2q':
        count = 0
        for line in args.file:
            body = json.loads(line)
            routingKey = args.routingKey or body.get('type')
            if not routingKey:
                raise ValueError('routingKey is not specified')
            msg = Message(body=body)
            manager.send(msg, args.exchange, routingKey)
            count += 1
        print('共发送%d条消息' % count)
    # 将队列的数据导出到文件
    elif args.action == 'q2f':
        count = 0
        if args.filename:
            df = open(args.filename, 'w')
        else:
            df = open(f'{args.queue}.dat', 'w')
        result = deque()
        for msg in iterQueue(manager, args.queue):
            if df:
                df.write(msg.Body + '\n')
                result.append(msg.Body)
                count += 1
        if df:
            df.close()
        print('从队列中共获取到%d条消息' % count)
        return '\n'.join(result)
    elif args.action == 'pub':
        message = {}
        if args.body.startswith('{') and args.body.endswith('}'):
            body = json.loads(args.body)
        else:
            body = {it[0]: it[1] for it in [
                tuple(item.split('=')) for item in args.body.split(',')]}
        if args.nobody:
            message.update(body)
        else:
            message['type'] = args.routingKey
            message['body'] = body
        manager.send(Message(body=message), args.exchange, args.routingKey)


if __name__ == '__main__':
    main()
