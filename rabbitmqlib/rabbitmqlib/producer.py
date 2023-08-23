#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-05-08 20:06:09

'''
from typing import Union
import pika
from .message import Message
import logging
import time
import pika.exceptions
import threading

class BlockingProducer:
    """使用BlockingConnection来发送消息, 确保消息发送正常送达
    """
    
    def __init__(self, url: str, confirmDelivery=True):
        """

        Args:
            url (str): amqp url
            ensureDelivery (bool, optional): 发送消息时确保消息送达. Defaults to True.
        """
        self.url = url
        self.confirmDelivery = confirmDelivery
        self.connect()
        # 总计发送消息数量
        self.messagePublished = 0
    
    def connect(self):
        """创建连接
        """
        self.connection = pika.BlockingConnection(
            pika.URLParameters(self.url)
        )
        self.channel = self.connection.channel()
        # 消息必须送达
        if self.confirmDelivery:
            self.channel.confirm_delivery()
            
    def publish(self, message: Message, exchange, routingKey):
        """发送消息

        Args:
            message (Message): _description_
            exchange (_type_): _description_
            routingKey (_type_): _description_
        """
        count = 0
        # 当连接中断时最多重试5次
        while count < 5:
            try:
                message.send(self.channel, exchange=exchange, routingKey=routingKey)
                self.messagePublished += 1
                if self.messagePublished % 1000 == 0:
                    logging.info('%d messages published', self.messagePublished)
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelWrongStateError) as e:
                # logging.exception(e)
                time.sleep(0.1)
                count += 1
                if count >= 5:
                    raise e
                logging.error('Connection Lost[%s], Trying to reconnect rabbitmq', str(e))
                self.connect()
            else:
                break
        
    def publishRaw(self, body: Union[str, dict], exchange: str, routingKey: str):
        """直接发送消息体

        Args:
            body (Union[str, dict]): 消息体, dict会自动json dump
            exchange (str): 
            routingKey (str): 
        """
        msg = Message(body=body)
        self.publish(message=msg, exchange=exchange, routingKey=routingKey)

    def close(self):
        """关闭连接"""
        if self.channel:
            self.channel.close()
        if self.connection:
            self.connection.close()


class ThreadSafeBlockingProducer(BlockingProducer):

    def __init__(self, url: str, confirmDelivery=True):
        super().__init__(url, confirmDelivery)
        self.lock = threading.RLock()
    
    def publish(self, message: Message, exchange, routingKey):
        with self.lock:
            super().publish(message, exchange, routingKey)
    
    def publishRaw(self, body: Union[str, dict], exchange: str, routingKey: str):
        with self.lock:
            super().publishRaw(body, exchange, routingKey)
    
    def scheduleHeartbeatForProducer(self):
        """生产者的blockconnection保持连接
        """
        with self.lock:
            # logging.info('sending heartbeat for producer')
            if not self.connection:
                logging.info('connection is not ready, cancel producer heartbeat')
                return
            self.connection.process_data_events()

    def start_loop(self):
        try:
            while True:
                self.scheduleHeartbeatForProducer()
                time.sleep(5)
        except Exception as e:
            self.close()
            raise e
