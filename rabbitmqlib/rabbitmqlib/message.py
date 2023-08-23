#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-02-05 18:29:08

'''
import base64
import json
from typing import Any, Dict, Tuple, Union, Optional
from datetime import datetime
import pika
from pika.spec import Basic
import time
from uuid import uuid4
import socket
from hashlib import md5

# 当前主机名
HOSTNAME = socket.gethostname()

class Message(object):

    def __init__(self, body: Union[dict, str, bytes],
                 channel=None, deliver: Optional[Basic.Deliver] = None, properties: Optional[pika.BasicProperties] = None, # type: ignore
                 messageType=None, parentId=None
                 ):
        """定义一个rabbitmq消息

        Args:
            body (Union[dict, str]): 消息体, dict或bytes会转换成str
            channel ([type], optional): 仅消费者接收的消息存在, 指消息来源的channel. Defaults to None.
            deliver (Basic.Deliver, optional): 消息发送者信息, 包含exchange和routingkey信息. Defaults to None.
            properties (pika.BasicProperties, optional): 消息属性, 新消息会自动创建. Defaults to None.
            messageType (str, optional): 消息类型, 接收消息不需要, 在properties中已经有, 创建消息指定. Defaults to None.
            parentId (str, optional): 父消息id, 仅创建消息时需要. Defaults to None.
        """
        # 消息的内容
        self.body: str = '{}'
        self._json = None
        self.Body = body
        # 消息来源的channel, 仅接收消息时存在, 发送消息时需要在send时指定channel, 防止channel失效
        self.channel = channel
        # 构造消息时不存在, 仅接收消息的时候存在, 是消息来源的一些信息
        self.deliver: Basic.Deliver = deliver  # type: ignore
        self.properties = properties or pika.BasicProperties(
            delivery_mode=2, message_id=str(uuid4()))
        if not self.properties.message_id:
            self.properties.message_id = str(uuid4())

        # 如果消息没有时间戳, 那就以当前时间作为时间戳
        if not self.Timestamp:
            self.setTimestamp()
        # 父消息id
        if parentId:
            self.setParentId(parentId)
        # 消息类型
        if messageType:
            self.properties.type = messageType

        # 消息处理是否失败
        self._failed = False
        self._fail_reason = '' # 失败原因

        # 消息的接收时间, 实例创建时间认为是消息的接收时间, 若输入参数中deliver不为空表示为接收到的消息, 才有_receive_time
        if deliver is not None:
            self._received_time = int(time.time())
        else:
            self._received_time = None
    
    def getHash(self, exchange='', routingKey='', includeExchange=True, includeRoutingKey=True):
        """
        获取消息体的md5, 这里只考虑exchange, routingKey和body, 不考虑消息的属性. 对于一个待发送的消息实际上exchange和routingKey都是空的, 

        Args:
            exchange (str, optional): exchange, 不为空的时候替换掉消息中的exchange. Defaults to ''.
            routingKey (str, optional): routingKey, 不为空时替换掉消息中的routingKey. Defaults to ''.
            includeExchange (bool, optional): md5中是否包含exchange. Defaults to True.
            includeRoutingKey (bool, optional): md5中是否包含routingKey. Defaults to True.

        Returns:
            str: md5的十六进制字符串
        """
        hashSeq = [self.Body]
        if includeExchange:
            hashSeq.append(exchange or self.Exchange)
        if includeRoutingKey:
            hashSeq.append(routingKey or self.RoutingKey)
        return md5('_'.join(hashSeq).encode('utf-8')).hexdigest()

    def markFailed(self, reason=''):
        """标记消息处理失败
        """
        self._failed = True
        self._fail_reason = reason
        
    def __getattr__(self, key):
        return self.json.get(key)

    @property
    def json(self) -> dict:
        if not self._json:
            self._json = json.loads(self.body)
        return self._json

    @property
    def Type(self):
        """消息的类型, type不存在的时候返回routing_key
        """
        return self.properties.type or self.RoutingKey

    @property
    def MessageId(self):
        """返回消息的唯一标识符
        """
        return self.properties.message_id

    @property
    def ParentId(self):
        """父消息id, 如果当前消息是由于另一个消息的处理而产生的, 则标记其parent
        """
        if self.properties.headers:
            return self.properties.headers.get('x-parent-id', None)
        else:
            return None

    def setParentId(self, parentId):
        if self.properties.headers:
            self.properties.headers['x-parent-id'] = parentId
        else:
            self.properties.headers = {'x-parent-id': parentId}

    @property
    def Body(self):
        return self.body

    @Body.setter
    def Body(self, body):
        if isinstance(body, dict):
            self.body = json.dumps(body, ensure_ascii=False)
            self._json = body
        elif isinstance(body, bytes):
            self.body = body.decode('utf-8')
            self._json = json.loads(self.body)
        else:
            self.body = body
            self._json = json.loads(self.body)
        if not isinstance(self._json, dict):
            raise ValueError('bad message body')

    @property
    def RoutingKey(self) -> str:
        """只对接收到的消息有效, 消息来源的routing_key
        """
        if self.deliver:
            return self.deliver.routing_key
        else:
            return ''

    @property
    def Exchange(self) -> str:
        """只对接收到的消息有效, 消息来源的exchange
        """
        if self.deliver:
            return self.deliver.exchange
        else:
            return ''

    @property
    def needReply(self) -> bool:
        """消息是否要响应
        """
        return True if self.properties.reply_to else False

    @property
    def ReplyTo(self) -> str:
        """消息要写入的回调队列
        """
        return self.properties.reply_to  # type: ignore

    @property
    def CorrId(self) -> str:
        return self.properties.correlation_id  # type: ignore

    @property
    def ConsumerTag(self) -> str:
        return self.deliver.consumer_tag

    @property
    def RedeliveredCount(self) -> int:
        """消息的重试次数
        """
        if self.properties.headers:
            return self.properties.headers.get('x-redelivered-count', 0)
        else:
            return 0

    def setCorrelationId(self, corrId):
        self.properties.correlation_id = corrId

    def setRedeliveredCount(self, count):
        """增加消息的重试次数计数
        """
        if self.properties.headers:
            self.properties.headers['x-redelivered-count'] = count
        else:
            self.properties.headers = {'x-redelivered-count': count}

    def setDurable(self, durable=True):
        """设置消息的持久化

        Args:
            durable (bool, optional): [description]. Defaults to True.
        """
        # self.properties.durable = durable
        self.properties.delivery_mode = 2 if durable else 1

    def setExpiration(self, ttl: int):
        """设置消息的过期时间
        """
        self.properties.expiration = str(ttl)

    def setPriority(self, priority):
        """设置消息优先级
        """
        self.properties.priority = priority

    def setReplyTo(self, replyTo):
        """设置回调队列
        """
        self.properties.reply_to = replyTo

    def send(self, channel, exchange, routingKey):
        """将消息发送出去, 注意deliver中的exchange和routing_key只有收到的消息有, 发送的消息不能设置
        """
        # 将消息的时间戳设置成当前时间
        self.setTimestamp()
        channel.basic_publish(exchange=exchange,
                              routing_key=routingKey,
                              body=self.Body,
                              properties=self.properties)
        self.properties.type = routingKey

    @property
    def ReceiveTime(self) -> datetime:
        """消息的接收时间"""
        if self._received_time is not None:
            return datetime.fromtimestamp(self._received_time)
        else:
            return None  # type: ignore

    @property
    def Timestamp(self) -> datetime:
        """消息发送时间的时间戳
        """
        timestamp = self.properties.timestamp
        if timestamp is None:
            return None  # type: ignore
        else:
            return datetime.fromtimestamp(timestamp)

    def setTimestamp(self):
        """设置消息的时间戳为当前时间
        """
        self.properties.timestamp = int(time.time())
        
    def shrinkBody(self, js=None, strSize=64):
        """压缩消息体, 字符串最长记录64个字符, 数组最多保留5个元素
        """
        if not js:
            js = dict(self.json)
        if isinstance(js, dict):
            return {
                k: self.shrinkBody(v, strSize=strSize) for k, v in js.items() if v
            }
        elif isinstance(js, list):
            return [self.shrinkBody(item, strSize=strSize) for item in js[:5] if item]
        elif isinstance(js, str):
            if len(js) > 64:
                return js[:64] + '...'
            else:
                return js
        else:
            return js

    def asLog(self) -> dict:
        """生成一条消息处理日志
        """
        log = dict(self.json)
        log: dict = self.shrinkBody(log)  # type: ignore
        log['_id'] = self.MessageId
        log['_message_type'] = self.Type
        log['_exchange'] = self.Exchange
        log['_routing_key'] = self.RoutingKey
        log['_parent_id'] = self.ParentId
        if self.Timestamp:
            log['_time'] = self.Timestamp.strftime('%Y-%m-%d %H:%M:%S')
        receive_time = self.ReceiveTime
        if receive_time is not None:
            log['_receive_time'] = receive_time.strftime('%Y-%m-%d %H:%M:%S')
            # 在k8s中, 主机名是pod的hostname, 某种程度上能够判断出是什么服务消费了这个消息
            log['_consumer_host'] = HOSTNAME

        log['_properties'] = {}
        for key in ('reply_to', 'expiration', 'priority', 'correlation_id'):
            val = getattr(self.properties, key)
            if val:
                log['_properties'][key] = val
        log['_redelivery_count'] = self.RedeliveredCount
        log['_failed'] = self._failed
        if self._failed:
            log['_failed_reason'] = self._fail_reason[:256]  # 最长留256个字符
        return log

    def asLogMessage(self) -> "Message":
        """生成一条日志消息"""
        return Message(body=self.asLog())
    
    def cloneProperties(self) -> pika.BasicProperties:
        """深拷贝当前属性
        """
        p = pika.BasicProperties(delivery_mode=2, message_id=str(uuid4()))
        if self.properties:
            for key in self.properties.__dict__:
                # 消息的id不可以clone
                if key == 'message_id':
                    continue
                v = getattr(self.properties, key)
                if v is not None:
                    if isinstance(v, dict):
                        setattr(p, key, dict(v))
                    else:
                        setattr(p, key, v)
        return p
    
    def clone(self) -> "Message":
        msg = Message(
            body=self.body,
            properties=self.cloneProperties()
        )
        msg.setParentId(self.MessageId)
        return msg
    
    def marshal(self, exchange: str = '', routingKey: str = '', withMessageId=False) -> str:
        """将消息以及消息要发送的目标转换成字符串

        Args:
            exchange (str): 拟发送的exchagne
            routingKey (str): 拟发送的routingKey
            withMessageId (bool): marshal的结果是否包含MessageId, 因为id是自动生成的,如果包含messageId则会导致每个新生成的消息hash都不一样.

        Returns:
            str: 
        """
        cloneProperty = self.cloneProperties()
        if withMessageId:
            cloneProperty.message_id = self.MessageId
        else:
            cloneProperty.message_id = ''
        properties = b''.join(cloneProperty.encode())
        encoded = {
            'properties': base64.b64encode(properties).decode(),
            'body': self.Body,
        }
        if exchange:
            encoded['exchange'] = exchange
        if routingKey:
            encoded['routingKey'] = routingKey
        return json.dumps(encoded, ensure_ascii=False, sort_keys=True)
    
    @classmethod
    def unMarshal(cls, s: str) -> Tuple["Message", str, str]:
        """将marshal()的结果还原成消息

        Args:
            s (str): marshal的结果

        Returns:
            Tuple[Message, str, str]: message, exchange, routingKey
        """
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        js = json.loads(s)
        properties = pika.BasicProperties()
        properties.decode(base64.b64decode(js['properties']))
        message = Message(body=js['body'], properties=properties)
        return (message, js.get('exchange', ''), js.get('routingKey', ''))
        

class MessageResult(object):
    """消息处理结果
    """

    def __init__(self, success: bool, result: Union[str, dict] = '', nextMessage=None):
        """

        Args:
            success (bool): 消息是否处理成功
            result (str, optional): 响应消息的body. Defaults to ''.
        """
        self.success = success
        self.result: Union[str, dict] = result
        # 消息处理后可能会产生的要继续处理的下游消息
        self.nextMessage: Optional[Message] = nextMessage 

    @property
    def Response(self):
        """响应的消息body
        """
        if isinstance(self.result, dict):
            return json.dumps(self.result, ensure_ascii=False)
        else:
            return self.result


class ReplyMessage(Message):
    """RPC的响应结构

    """

    SUCCESS = 0
    ERROR = 1
    # 消息被缓存
    BUFFERED = 2

    def __init__(self, code=0, message='', body: Union[Dict[str, Any], str] = {}):
        # 返回编码
        self.code = code
        # 错误提示信息
        self.message = message
        # 消息处理后的返回体, 处理方定义, 如果非空必须是一个json字符串
        if isinstance(body, str):
            body = json.loads(body)
        msgBody = {
            'code': self.code
        }
        if message:
            msgBody['message'] = message
        if body:
            msgBody['body'] = body
        super().__init__(json.dumps(msgBody, ensure_ascii=False))
