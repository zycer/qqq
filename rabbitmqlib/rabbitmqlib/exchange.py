#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-02-05 18:41:01

'''
import functools
from .message import Message
import logging


class ExchangeProcessor(object):

    def __init__(self, name: str, delayExchange=None, type='topic', durable=True, receiveAllQueue=None):
        """

        Args:
            name ([type]): exchange名称
            delayExchange ([type], optional): exchange对应的延迟队列, 如果要延迟发送则发送给延迟队列. Defaults to None.
            type (str, optional): exchange类型, 目前实际只支持topic. Defaults to 'topic'.
            durable (bool, optional): exchange是否持久化. Defaults to True.
            receiveAllQueue ([type], optional): 是否创建一个队列接受exchange的全部数据. Defaults to None.
        """
        if not name:
            self.delayExchange = None
            self.name = ''
            self.receiveAllQueue = None
        else:
            self.name = name
            self.delayExchange = delayExchange
            self.receiveAllQueue = receiveAllQueue
        self.type = type
        self.durable = durable
        self._exchange_ready = False
        self._delay_exchange_ready = False

    @property
    def Ready(self):
        return self._exchange_ready and self._delay_exchange_ready

    def setExchangeReady(self):
        logging.info('%s set exchange ready', self.name)
        self._exchange_ready = True

    def declareExchange(self, channel, callback):
        # 默认交换机, 不需要declare, 也不存在延迟队列了
        logging.info('declaring exchange %s', self.name)
        if not self.name:
            self._exchange_ready = True
            self._delay_exchange_ready = True
            return callback()
        # 创建交换机
        cb1 = functools.partial(self.declareReceiveAllQueue, channel=channel)

        def cb(method):
            cb1(method)
            callback()

        channel.exchange_declare(
            exchange=self.name,
            exchange_type=self.type,
            durable=True,
            callback=cb)
        logging.info('create exchange %s finished', self.name)
        # 创建延迟交换机
        if self.delayExchange:
            logging.info('declaring exchange %s', self.delayExchange)
            cb2 = functools.partial(self.declareDelayQueue, channel=channel)
            channel.exchange_declare(
                exchange=self.delayExchange,
                exchange_type=self.type,
                durable=True,
                callback=cb2)
        else:
            self._delay_exchange_ready = True

    def declareDelayQueue(self, method, channel):
        """创建延迟队列, 延迟队列对应的死信交换机是当前交换机
        """
        logging.info('declare queue: %s', self.delayExchange)
        arguments = {"x-dead-letter-exchange": self.name}
        # 不指定routing_key, 则routing_key和原消息一致
        cb = functools.partial(self.bindDelayQueue, channel=channel)
        channel.queue_declare(
            queue=self.delayExchange,  # 队列名和交换机名一致
            callback=cb, durable=True,
            arguments=arguments
        )

    def bindDelayQueue(self, method, channel):
        """绑定延迟队列"""
        logging.info('binding queue: %s to exchange: %s',
                     self.delayExchange, self.delayExchange)
        channel.queue_bind(
            self.delayExchange,
            self.delayExchange,
            routing_key='#')
        self._delay_exchange_ready = True

    def declareReceiveAllQueue(self, method, channel):
        """创建一个队列接受交换机所有数据, 主要用于处理死信交换机
        """
        if not self.receiveAllQueue:
            self.setExchangeReady()
            return
        logging.info('declare queue: %s', self.name)
        cb = functools.partial(self.bindReceiveAllQueue, channel=channel)
        channel.queue_declare(
            queue=self.name,  # 队列名和交换机名一致
            callback=cb, durable=True
        )

    def bindReceiveAllQueue(self, method, channel):
        """绑定接受全部数据的队列
        """
        if self.receiveAllQueue:
            logging.info('bind queue: %s to exchange %s',
                         self.receiveAllQueue, self.name)
            channel.queue_bind(
                self.receiveAllQueue,
                self.name,
                routing_key='#')
        self.setExchangeReady()

    def send(self, producer, message: Message, routingKey, delay=0):
        """发送消息

        Args:
            message (Message): 消息
            delay: 延迟发送时间, 单位为毫秒
        """
        if delay > 0 and self.delayExchange is not None:
            # 延迟处理消息
            message.setExpiration(delay)
            producer.publish(message, exchange=self.delayExchange, routingKey=routingKey)
            #message.send(channel, exchange=self.delayExchange,
            #             routingKey=routingKey)
        else:
            producer.publish(message, exchange=self.name, routingKey=routingKey)
            #message.send(channel, exchange=self.name,
            #             routingKey=routingKey)


class DeadExchangeProcessor(ExchangeProcessor):

    def __init__(self, name):
        super().__init__(name, receiveAllQueue=name)


class DefaultExchangeProcessor(ExchangeProcessor):

    def __init__(self):
        super().__init__(name='')
