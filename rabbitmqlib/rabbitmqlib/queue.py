#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-02-05 19:01:00

'''

from datetime import datetime
from collections import deque
import functools
from .exchange import ExchangeProcessor
from .message import Message, MessageResult, ReplyMessage
import logging
import time
from threading import Event
from typing import Optional
from threading import Thread
from multiprocessing.pool import ThreadPool


def defaultCallback(message: Message) -> Optional[MessageResult]:
    """默认消息处理函数, 仅仅是打log
    """
    logging.info(message.json)
    return MessageResult(True)


class QueueProcessor(object):

    def __init__(self, name: str, exchangeProcessor: ExchangeProcessor, callback=defaultCallback,
                 routingKey="", autoAck=False, exclusive=False,
                 durable=True, deadExchange=None, deadRoutingKey=None,
                 retryTimes=0, retryDelay=60000, withPriority=False,
                 autoDelete=False, interval=0, threaded=False):
        """

        Args:
            name (str): 队列名称
            callback ([type], optional): 消息的回调函数. Defaults to defaultCallback.
            exchangeProcessor (str, optional): 对应的exchange. Defaults to "".
            routingKey (str, optional): 绑定的routing_key, 不指定时与队列名称相同. Defaults to "".
            durable (bool, optional): 队列是否需要持久化. Defaults to True.
            deadExchange (str, optional): 死信队列. Defaults to None.
            deadRoutingKey (str, optional): 发送到死信队列时使用的routing_key, 默认使用原消息的routing_key. Defaults to None.
            retryTimes(int): 消息的重试次数, 注意指定回调队列的消息不重试. Defaults to 0.
            retryDelay(int): 重试间隔, 单位毫秒, 默认1分钟
            withPriority(bool): 支持设置优先级    Defaults to False.
            autoDelete(bool): 消费者下线后自动删除 Defaults to False.
            interval(int): 两次消息处理的最小间隔, 若与上次接收时间的间隔小于interval, 则直接失败让其重试. 0表示不做处理.  Defaults to 0.
            threaded(bool): 将callback放到线程中执行
        """
        self.name = name
        if not self.name:
            self.routingKey = self.name = 'autogen_%s' % datetime.utcnow().strftime(
                '%Y%m%d%H:%M:%S.%f')
        else:
            self.routingKey = routingKey or self.name
        self.callback = callback or defaultCallback
        self.exchangeProcessor = exchangeProcessor

        # routingKey不指定则与队列名一致
        self.durable = durable
        self.deadExchange = deadExchange
        self.deadRoutingKey = deadRoutingKey
        self.consumerTag = None
        self.retryTimes = retryTimes
        self.retryDelay = retryDelay
        self.autoAck = autoAck
        self.exclusive = exclusive
        self.withPriority = withPriority
        self.autoDelete = autoDelete
        self.interval = interval
        self.threaded = threaded

        # RabbitmqManager
        self._manager = None  # type: ignore
        
        # 记录累计拒绝/确认/重试的消息数量
        self._reject_count = 0
        self._ack_count = 0
        self._retry_count = 0

    def setManager(self, mgr):
        self._manager = mgr

    @property
    def ExchangeName(self):
        return self.exchangeProcessor.name

    @property
    def DelayExchange(self):
        return self.exchangeProcessor.delayExchange
    
    def processMessage(self, message: Message) -> Optional[MessageResult]:
        """处理消息
        """
        if not self.threaded:
            return self.callback(message)
        else:
            pool = ThreadPool(processes=1)
            asyncResult = pool.apply_async(self.callback, args=(message, ))
            startTs = time.time()
            while not asyncResult.ready():
                self._manager.heartbeat()
                asyncResult.wait(0.1)
            endTs = time.time()
            if endTs - startTs > 10:
                logging.info('processMessage cost %f seconds', endTs-startTs)
            return asyncResult.get()
            
    def declareQueue(self, channel):
        """创建队列"""
        logging.info(f'declare queue {self.name}')
        arguments = {}
        if self.withPriority:
            arguments["x-max-priority"] = 10
        if self.deadExchange:
            arguments["x-dead-letter-exchange"] = self.deadExchange
        if self.deadRoutingKey:
            arguments["x-dead-letter-routing-key"] = self.deadRoutingKey
        cb = functools.partial(self.bindQueue, channel=channel)
        channel.queue_declare(
            queue=self.name,
            callback=cb, durable=self.durable,
            arguments=arguments,
            exclusive=self.exclusive,
            auto_delete=self.autoDelete
        )

    def bindQueue(self, methodFrame, channel):
        """绑定队列到交换机"""
        logging.info(f'Queue({self.name}) declare ok')
        if not self.ExchangeName:
            self.consume(methodFrame, channel)
            return
        cb = functools.partial(self.consume, channel=channel)
        channel.queue_bind(
            self.name,
            self.ExchangeName,
            routing_key=self.routingKey,
            callback=cb)

    def onMessage(self, channel, basic_deliver, properties, body):
        """接受消息回调函数
        """
        try:
            msg = Message(body, channel, basic_deliver, properties)
        except Exception as e:
            logging.exception('message has bad format, %s', body)
            logging.exception(e)
            
            # TODO: 消息格式异常的没有记录到日志中
            channel.basic_reject(
                delivery_tag=basic_deliver.delivery_tag, requeue=False)
            return
            
            
        # logging.info(f'Received msg: routingkey({msg.RoutingKey}), {body}')
        result = MessageResult(False)
        err = None
        try:
            # 如果消息距离上次处理时间小于self.interval, 则直接失败
            if self.interval > 0 and self._manager and self._manager.isDuplicateMessage(msg, self.interval):
                result = MessageResult(False, result='距离上次处理时间小于%s秒' % self.interval)
            else:
                result = self.processMessage(msg)
        except Exception as e:
            err = e
            logging.exception(e)
        finally:
            # callback返回None表示处理成功
            if result is None:
                result = MessageResult(True)
            # 需要应答的消息发送应答
            if msg.needReply:
                self.reply(channel, msg, result)
            # 处理不成功判断是否需要重试
            if not result.success:
                msg.markFailed(str(result.result))
                if self.needRetry(msg):
                    self.retry(channel, msg)
                else:
                    self.reject(channel, msg)
            else:
                self.ack(channel, msg)
            if isinstance(err, OSError):
                logging.error('unrecoverable error, stop consumer')
                self._manager.stop()

    def reply(self, channel, message: Message, result: MessageResult):
        """rpc消息回复

        Args:
            message (Message): 原始消息
            result (MessageResult): 消息的处理结果
        """
        replyMessage = ReplyMessage(
            code=ReplyMessage.BUFFERED if not result else ReplyMessage.SUCCESS if result.success else ReplyMessage.ERROR,
            body=result.result if result and result.result else '{}'
        )
        replyMessage.setParentId(message.MessageId)
        replyMessage.setCorrelationId(message.CorrId)
        # 发送消息
        self._manager.send(message, exchange='',         # type: ignore
                           routingKey=message.ReplyTo)   # type: ignore

    def ack(self, channel, message: Message):
        """确认消息
        """
        if self._manager:
            self._manager.logMessage(message)
        self._ack_count += 1
        if self._ack_count % 1000 == 0:
            logging.info('%d msgs are acked', self._ack_count)
        if self.autoAck:
            return
        # logging.info('Acknowledging message %s', message.deliver.delivery_tag)
        channel.basic_ack(message.deliver.delivery_tag)

    def reject(self, channel, message: Message):
        """拒绝消息
        """
        if self._manager:
            self._manager.logMessage(message)
        # 拒绝消息一律不回写如队列, 重试通过retry来控制
        channel.basic_reject(
            delivery_tag=message.deliver.delivery_tag, requeue=False)
        self._reject_count += 1
        logging.warning('Reject message: %s', message.Body[:256])
        logging.info('%d msgs are rejected', self._reject_count)

    def needRetry(self, message: Message):
        """消息是否需要重试"""
        # 需要应答的消息不重试, 因为重试了接收方也收不到了
        if message.needReply:
            return False
        if message.RedeliveredCount >= self.retryTimes:
            return False
        return True

    def retry(self, channel, message: Message):
        """重试消息
        """
        # 先确认, 再重新发送一个消息
        self.ack(channel, message)

        retryMessage = message.clone()
        # 增加重试次数
        retryMessage.setRedeliveredCount(message.RedeliveredCount + 1)
        # self.send(channel, retryMessage, delay=self.retryDelay)
        self._manager.send(retryMessage, self.ExchangeName, message.RoutingKey, self.retryDelay)  # type: ignore
        
        self._retry_count += 1
        logging.warning('Retrying message the %d times: %s', message.RedeliveredCount, message.Body[:256])

    def send(self, channel, message: Message, delay=0):
        """发送消息

        Args:
            message (Message): 消息
            delay: 延迟发送时间, 单位为毫秒
        """
        self._manager.send(message, self.ExchangeName,    # type: ignore
                           self.routingKey, delay)   # type: ignore

    # def startConsume(self, channel):
    #    """开始消费
    #    """
    #    while not self.exchangeProcessor.Ready:
    #        #time.sleep(1)
    #        logging.info('Waiting for exchange init')
    #    self.declareQueue(channel)

    def consume(self, _unused_frame, channel):
        logging.info('begin to  consume %s', self.name)
        self.consumerTag = channel.basic_consume(
            self.name, on_message_callback=self.onMessage, auto_ack=self.autoAck)


class CallbackQueueProcessor(QueueProcessor):

    def __init__(self, exchangeProcessor, callback):
        super().__init__('', exchangeProcessor,
                         callback=callback, autoAck=True, exclusive=True)


class BufferedQueueProcessor(QueueProcessor):
    """允许消息被缓存, 统一处理后再批量确认
    """

    MESSAGE_RESULT_BUFFERED = None

    def __init__(self, name: str, exchangeProcessor: ExchangeProcessor, callback=defaultCallback,
                 routingKey="", autoAck=False, exclusive=False,
                 durable=True, deadExchange=None, deadRoutingKey=None,
                 retryTimes=0, retryDelay=60000, withPriority=False,
                 flush_interval=10, autoDelete=False, interval=0, threaded=False
                 ):
        super().__init__(name=name, exchangeProcessor=exchangeProcessor, callback=callback,
                         routingKey=routingKey, autoAck=autoAck,
                         exclusive=exclusive, durable=durable, deadExchange=deadExchange,
                         deadRoutingKey=deadRoutingKey, retryTimes=retryTimes,
                         retryDelay=retryDelay, withPriority=withPriority, autoDelete=autoDelete, interval=interval, threaded=threaded)

        # 缓存消息
        self._cache = deque()
        # 没有新消息时的刷新缓存间隔, 单位是秒
        self.flush_interval = flush_interval
        # 上次确认消息的时间
        self.last_ack_time = time.time()
        self.flush_event = Event()
        self.flush_event.clear()

    def flushCache(self, channel):
        """向callback发送空消息, callback收到空消息时应处理所有缓存的消息"""
        self.flush_event.clear()
        now = time.time()
        if self._cache and now - self.last_ack_time >= self.flush_interval:
            result = MessageResult(False)
            try:
                result = self.callback(None)
            except Exception as e:
                logging.exception(e)
            finally:
                # 处理成功则全部确认, 否则全部拒绝
                if result.success:
                    self.clearCache(channel)
                else:
                    self.clearCache(channel, reject=True)
                self.last_ack_time = now
        else:
            self.scheduleNextFlush(channel)

    def scheduleNextFlush(self, channel):
        """创建一个刷新任务
        """
        # 如果已经有一个刷新任务了,跳过
        if not self.flush_event.is_set():
            self.flush_event.set()
            cb = functools.partial(self.flushCache, channel=channel)
            self._manager._connection.ioloop.call_later(1, cb)

    def clearCache(self, channel, reject=False):
        """
            批量确认缓冲区中的消息
        """
        for msg in self._cache:
            if reject:
                if self.needRetry(msg):
                    self.retry(channel, msg)
                else:
                    self.reject(channel, msg)
            else:
                self.ack(channel, msg)
        self._cache.clear()
    
    def onMessage(self, channel, basic_deliver, properties, body):
        """接受消息回调函数
        """
        # logging.info('Received msg: %s', body[:128])
        try:
            msg = Message(body, channel, basic_deliver, properties)
        except Exception as e:
            logging.exception('message has bad format, %s', body)
            logging.exception(e)
            
            # TODO: 消息格式异常的没有记录到日志中
            channel.basic_reject(
                delivery_tag=basic_deliver.delivery_tag, requeue=False)
            return
        result = MessageResult(False)
        try:
            # result为None表示callback缓存了消息没有处理
            # result.success为False表示缓存的消息都处理失败了
            # result.success为True表示缓存的消息都处理成功了
            result = self.callback(msg)
        except Exception as e:
            logging.exception(e)
        finally:
            self._cache.append(msg)
            # result为None表示没有处理而是缓存了
            if result is None:
                self.scheduleNextFlush(channel)
            else:
                if result.success:
                    self.clearCache(channel)
                else:
                    self.clearCache(channel, reject=True)
                self.last_ack_time = time.time()
