#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-12-20 17:32:37

'''
from rabbitmqlib.rabbitmqlib.message import Message
from rabbitmqlib.rabbitmqlib import RabbitMqManager
import time
from argparse import ArgumentParser

def callback(message: Message):
    print(message.Body)
    print('retry count: %s' % message.RedeliveredCount)
    count = 1
    while count < 620:
        raise OSError()
        time.sleep(1)
        count += 1
        print(count)
    print('message process over')
    

def getArgs():
    parser = ArgumentParser()
    parser.add_argument('--url', dest='mqUrl', default='amqp://rxthinking:gniknihtxr@192.168.101.155:42158/%2F?socket_timeout=3000&stack_timeout=3000')
    parser.add_argument('--exchange', dest='exchange', default='test')
    parser.add_argument('--routing', dest='routingKey', default='test')
    return parser.parse_args()


def main():
    args = getArgs()
    manager = RabbitMqManager(args.mqUrl)
    manager.listen(
        args.routingKey, args.exchange, callback=callback, threaded=False, retryTimes=3
    )
    manager.listen(
        f'{args.routingKey}-1', args.exchange, callback=callback, threaded=False, retryTimes=3
    )
    manager.run()

main()
    

    