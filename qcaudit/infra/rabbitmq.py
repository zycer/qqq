#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-25 14:51:22

'''
import pika
import json
import logging
import time

class RabbitMQ:
    logging.getLogger("pika").setLevel(logging.INFO)

    def __init__(self, url):
        self.url = url
        self.connection = None
        self.channel = None
        self.connect()
    
    def connect(self):
        self.connection = pika.BlockingConnection(
            pika.URLParameters(self.url)
        )
        self.channel = self.connection.channel()
    
    def publish(self, message: dict, exchange='qcetl', routing_key=''):
        """发送消息

        Args:
            message (dict): [description]
            exchange (str, optional): [description]. Defaults to 'qcetl'.
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
        except Exception as e:
            logging.exception(e)
            self.channel = None
            self.connection = None
            time.sleep(0.1)
            logging.info("reconnect")
            self.connect()
            self.publish(message, exchange, routing_key)
