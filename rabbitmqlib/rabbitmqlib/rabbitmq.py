#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-01-09 10:06:37

'''

import pika.exceptions
from .producer import BlockingProducer
from .queue import BufferedQueueProcessor, QueueProcessor
from typing import Callable, Dict, Optional
from .exchange import DeadExchangeProcessor, ExchangeProcessor
import pika
import logging
import functools
from .message import Message, MessageResult
import time
from pika.channel import Channel
from .scheduler import MessageScheduler
from apscheduler.schedulers.background import BackgroundScheduler
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', datefmt='%m-%d %H:%M:%S')


class RabbitMqManager(object):

    def __init__(self, url: str, prefetchCount=1, logExchange=None, logRoutingKey=None, redisUrl='', schedulerRedisKey=MessageScheduler.DEFAULT_KEY, confirmDelivery=True):
        """

        Args:
            url (str): rabbitmq的amqp url
            prefetchCount (int, optional): 预取条数, 除非对时效性没有要求, 否则使用默认值1即可. 超过1时消费者会预读取消息, 这样如果消息处理时间长就会导致延迟增加. Defaults to 1.
            logExchange (str, optional): 记录日志消息的exchange. Defaults to None.
            logRoutingKey (str, optional): 记录日志消息的routing key. Defaults to None.
            redisUrl (str, optional): redis地址, 用于定时发送消息
            confirmDelivery(bool): 生产者发送消息是否需要确认, 默认开启, 关闭后发送消息速度会更快, 但是在消息发送完成后需要手动刷新
        """
        self.url = url

        # 所有管理的exchange
        self._exchanges: Dict[str, ExchangeProcessor] = {}
        # 所有管理的queue
        self._queues: Dict[str, QueueProcessor] = {}
        self.should_reconnect = False
        # 曾经启动过消费者
        self.was_consuming = False

        self._reconnect_delay = 0
        self._connection: pika.SelectConnection = None  # type: ignore
        self._channel: Channel = None  # type: ignore
        # 正在处理连接关闭事件
        self._closing = False
        # 正在消费
        self._consuming = False
        # In production, experiment with higher prefetch values
        # for higher consumer throughput
        # 消息预取条数, 通常情况下建议保持默认值1, 当使用BufferedQueueProcessor时根据需要批量处理的大小来设置
        self._prefetchCount = prefetchCount

        # 日志交换机和日志routingkey
        self._logExchange = logExchange
        self._logRoutingKey = logRoutingKey

        # 异步运行的线程
        self._thread = None
        # 生产者, 生产者用blockingconnection实现, 确保消息送达
        self._producer = BlockingProducer(self.url, confirmDelivery=confirmDelivery)
        
        # 消息调度器
        self._scheduler = None
        if redisUrl:
            self._scheduler = MessageScheduler(redisUrl=redisUrl, redisKey=schedulerRedisKey)

    def send(self, message: Message, exchange: str, routingKey: str, delay: int = 0, writeLog=True, dueTime=None):
        """发送消息

        Args:
            message (Message): 消息本身
            exchange (str): 要发送的交换机, 必须在_exchanges中存在
            routingKey (str): 发送的routing_key
            delay (int, optional): 延迟发送时间. Defaults to 0.
        """
        # logging.info('#%s:%s Sent Message: %s, Delay: %s ms', message.MessageId, message.Type, message.Body[:128], delay)
        # 指定预约发送时间时, 忽略delay, 并且不记录日志, 日志将会在消息真实发送后才记录
        if dueTime is not None:
            if self._scheduler is not None:
                self._scheduler.schedueByTime(message=message, exchange=exchange, routingKey=routingKey, dueTime=dueTime)
            else:
                raise ValueError('Scheduler is not initialized, cannot send scheduled message')
        if exchange in self._exchanges:
            self._exchanges[exchange].send(
                self._producer, message, routingKey, delay)
        else:
            self._producer.publish(
                message, exchange=exchange, routingKey=routingKey)
        # self.addPendingPublishMessage()
        # 假设消息发送都是成功的, 如果发送失败就没有记录日志
        if writeLog:
            self.logMessage(message)

    def logMessage(self, message: Message):
        """记录消息日志
        """
        if self._logExchange and self._logRoutingKey:
            logMessage = Message(message.asLog())
            self.send(logMessage, exchange=self._logExchange,
                      routingKey=self._logRoutingKey, writeLog=False)
            
    def isDuplicateMessage(self, message: Message, interval=60):
        """检查消息是否是重复消息, 即interval秒内曾经处理过
        """
        if self._scheduler:
            return self._scheduler.isDuplicateMessage(message, interval)
        else:
            return False

    def addExchangeProcessor(self, exchange: str, delayExchange=None, durable=True):
        """添加一个交换机

        Args:
            exchange (str): exchange名称
            delayExchange ([type], optional): [description]. Defaults to None.
            durable (bool, optional): 是否持久化. Defaults to True.
        """
        if exchange not in self._exchanges:
            self._exchanges[exchange] = ExchangeProcessor(
                exchange, delayExchange=delayExchange, durable=durable)
        return self._exchanges[exchange]

    def addDeadExchangeProcessor(self, exchange: str):
        """添加一个死信交换机
        """
        if exchange not in self._exchanges:
            self._exchanges[exchange] = DeadExchangeProcessor(exchange)
        return self._exchanges[exchange]

    def listen(self, name: str, exchange: str, callback: Callable[[Message], Optional[MessageResult]],
               routingKey="",
               durable=True, deadExchange=None, deadRoutingKey=None,
               retryTimes=0, retryDelay=60000, flush_interval=0, 
               exclusive=False, autoDelete=False, interval=0, threaded=False):
        """ 监听一个队列
        Args:
            name (str): 队列名称, 队列名称的命名建议使用  {服务名称}.{exchange}.{routingKey}. name不与routingKey相同时一定要指定routingKey. 队列与exchange和queue的binding会自动创建. 注意如果此前手动创建过queue, 那么有可能由于死信队列等参数配置不一致导致RabbitMqManager无法启动, 此时应手动删除队列后让RabbitMqManager自动创建队列.
            callback ([type], optional): 消息的回调函数. Defaults to defaultCallback.
            exchange (str, optional): 对应的exchange, 会自动创建. Defaults to "".
            routingKey (str, optional): 绑定的routing_key, 不指定时与队列名称相同. Defaults to "".
            durable (bool, optional): 队列是否需要持久化. Defaults to True.
            deadExchange (str, optional): 死信队列. Defaults to None.
            deadRoutingKey (str, optional): 发送到死信队列时使用的routing_key, 默认使用原消息的routing_key. Defaults to None.
            retryTimes(int): 消息的重试次数, 注意指定回调队列的消息不重试
            retryDelay(int): 重试间隔, 单位毫秒, 默认1分钟
            flush_interval(int): 刷新消息间隔, 当大于0时表示消息可能会被callback缓存下来批量处理, 此时不应该依赖于消息的reply, 因为reply的时候可能还没有拿到消息处理结果
            exclusive(bool): 排他队列, 不允许其他消费者消费
            autoDelete(bool): 自动删除, 当没有消费者时就自动删除. 
            interval(int): 距离上次消息处理时间的最小间隔, 小于最小间隔则直接失败. 
            threaded(bool): 将callback函数放到线程中执行, 避免时间超长的任务心跳失败
        """
        if exchange not in self._exchanges:
            self.addExchangeProcessor(
                exchange, delayExchange=f'{exchange}.delay')
        if deadExchange and deadExchange not in self._exchanges:
            self.addDeadExchangeProcessor(deadExchange)
        # 当指定刷新间隔时表示允许消费者缓存消息, 此时_prefetchCount必须大于1否则会降级成普通队列处理方式
        if flush_interval > 0 and self._prefetchCount > 1:
            queue = BufferedQueueProcessor(
                name, exchangeProcessor=self._exchanges[exchange],
                callback=callback, routingKey=routingKey,
                durable=durable, deadExchange=deadExchange, deadRoutingKey=deadRoutingKey,
                retryTimes=retryTimes, retryDelay=retryDelay, flush_interval=flush_interval,
                threaded=threaded
            )
        else:
            queue = QueueProcessor(
                name, exchangeProcessor=self._exchanges[exchange],
                callback=callback, routingKey=routingKey,
                durable=durable, deadExchange=deadExchange, deadRoutingKey=deadRoutingKey,
                retryTimes=retryTimes, retryDelay=retryDelay, exclusive=exclusive,
                autoDelete=autoDelete, interval=interval, threaded=threaded
            )
        self._addQueueProcessor(queue)
        return queue

    addQueueProcessor = listen

    def _addQueueProcessor(self, queue: QueueProcessor):
        queue.setManager(self)
        self._queues[queue.name] = queue
        return queue

    def run(self):
        while True:
            try:
                # 重新运行时清空pending的消息, 反正也无法再送达了
                self._run()
            # 手动退出时不重试, 如果是连接中断尝试重新连接
            except KeyboardInterrupt:
                self.stop()
                break
            self._maybe_reconnect()
            if not self.should_reconnect:
                break

    def runAsync(self, wait=True):
        """
        在一个独立的线程中启动, 不影响主线程的使用

        Args:
            wait (bool, optional): 等待连接初始化完成. Defaults to True.
        """
        from threading import Thread
        thread = Thread(target=self._run)
        thread.setDaemon(True)
        thread.start()
        self._thread = thread
        if wait:
            while not self._consuming:
                logging.info('waiting for connection')
                time.sleep(1)

    def stopAsync(self):
        """停止异步线程"""
        if self._thread:
            self.stop()
            self._thread.join()

    def connect(self) -> pika.SelectConnection:
        """连接到mq
        """
        logging.info('Connecting to %s', self.url)
        return pika.SelectConnection(
            parameters=pika.URLParameters(self.url),
            on_open_callback=self.onConnectionOpen,
            on_open_error_callback=self.onConnectionOpenError,
            on_close_callback=self.onConnectionClosed)

    def closeConnection(self):
        """关闭连接
        """
        self._consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            logging.info('Connection is closing or already closed')
        else:
            logging.info('Closing connection')
            self._connection.close()

    def onConnectionOpen(self, _unused_connection):
        """连接建立, 创建channel
        """
        logging.info('Connection opened')
        self.openChannel()

    def onConnectionOpenError(self, _unused_connection, err):
        """连接失败,重新连接
        """
        logging.error('Connection open failed: %s', err)
        self.reconnect()

    def onConnectionClosed(self, _unused_connection, reason):
        """连接中断
        """
        self._channel = None  # type: ignore
        if self._closing:
            self._connection.ioloop.stop()
            logging.info('Stopped')
        else:
            self.stop()

    def reconnect(self):
        """连接中断, 可以重试连接, 目前没有处理, 失败了就让容器自己挂了重启
        """
        self.should_reconnect = True
        self.stop()

    def openChannel(self):
        """打开一个channel
        """
        logging.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.onChannelOpen)

    def onChannelOpen(self, channel):
        """channel成功打开, 创建exchange
        """
        logging.info('Channel opened')
        self._channel = channel
        # self._channel.confirm_delivery(self.on_delivery_confirmation)
        self._channel.add_on_close_callback(self.onChannelClosed)
        self.startConsume()

    def onChannelClosed(self, channel, reason):
        # channel被broker关闭, 通常是连接参数错误
        logging.warning('Channel %i was closed: %s, %s',
                        channel, reason, type(reason))
        self.closeConnection()

    def onExchangeOkCallback(self, exchange):
        """交换机创建成功回调函数"""
        logging.info('%s declare ok', exchange.name)
        for queue in self._queues.values():
            if queue.ExchangeName == exchange.name:
                queue.declareQueue(self._channel)

    def startConsume(self):
        """所有队列开始消费消息"""
        logging.info('Issuing consumer related RPC commands')
        self._channel.basic_qos(
            prefetch_count=self._prefetchCount)
        self._channel.add_on_cancel_callback(self.onConsumerCancelled)
        for exchange in self._exchanges.values():
            callback = functools.partial(
                self.onExchangeOkCallback, exchange=exchange)
            exchange.declareExchange(self._channel, callback)
        # wait for exchange declare ok
        # for queue in self._queues.values():
        #    queue.startConsume(self._channel)
        self.was_consuming = True
        self._consuming = True
        # 生产者启动心跳
        self.scheduleHeatbeatForProducer()

    def onConsumerCancelled(self, method_frame):
        """远程取消连接回调"""
        logging.info('Consumer was cancelled remotely, shutting down: %r',
                     method_frame)
        if self._channel:
            self._channel.close()

    def stopConsume(self):
        """停止消费消息
        """
        if self._channel:
            logging.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            # 只有在所有消费者都停止的情况下, 才能关闭channel
            runningConsumerTags = set([queue.consumerTag for queue in self._queues.values()])
            for queue in self._queues.values():
                logging.info('trying to cancel %s: %s', queue.name, queue.consumerTag)
                cb = functools.partial(self.onCancelOk, consumerTag=queue.consumerTag, runningConsumerTags=runningConsumerTags)
                self._channel.basic_cancel(queue.consumerTag, cb)

    def onCancelOk(self, frame, consumerTag: str, runningConsumerTags: set):
        """消费者取消的回调. 由于可能同时监听多个队列, 所以需要等待所有消费者都取消才能关闭channel

        Args:
            frame (_type_): 
            consumerTag (str): 消费者的tag
            runningConsumerTags (set): 所有等待取消的消费者tag
        """
        runningConsumerTags.remove(consumerTag)
        if not runningConsumerTags:
            logging.info('%s is canceled, all consumer canceled ok', consumerTag)
            self._consuming = False
            self.closeChannel()
        else:
            logging.info('%s is canceled, waiting other consumers[%s]', consumerTag, ','.join(runningConsumerTags))

    def closeChannel(self):
        logging.info('Closing the channel')
        self._channel.close()

    def _run(self):
        """开始处理消息
        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        if not self._closing:
            self._closing = True
            logging.info('Stopping')
            if self._consuming:
                self.stopConsume()
                try:
                    # 这里有可能是由于ctrl-c进来导致ioloop已经不在运行状态了, 而pika的所有回调都基于ioloop, 所以要重启, 应该有更优雅的办法判断ioloop是不是running状态
                    self._connection.ioloop.start()
                except:
                    pass
            else:
                self._connection.ioloop.stop()
                logging.info('Stopped')

    def _maybe_reconnect(self):
        if self.should_reconnect:
            self.stop()
            reconnect_delay = self._get_reconnect_delay()
            logging.info('Reconnecting after %d seconds', reconnect_delay)
            time.sleep(reconnect_delay)

    def _get_reconnect_delay(self):
        if self.was_consuming:
            self._reconnect_delay = 0
        else:
            self._reconnect_delay += 1
        if self._reconnect_delay > 30:
            self._reconnect_delay = 30
        return self._reconnect_delay

    def fetchAndSendScheduledMessages(self):
        """从redis获取已到期的定时发送的消息发送出去
        """
        if not self._scheduler:
            return
        for message, exchange, routingKey in self._scheduler.fetchExpiredMessages():
            self.send(message, exchange=exchange, routingKey=routingKey)
    
    def heartbeat(self):
        """保持心跳
        """
        self._connection.ioloop.poll()
        self._connection.ioloop.process_timeouts()
            
    def startScheduler(self, block=True):
        """每10秒检查一下redis中是否有需要发送的消息
        """
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.fetchAndSendScheduledMessages, 'interval', seconds=10)

        scheduler.start()
        
        if block:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                scheduler.shutdown()
                logging.warning('Manually stopped')
    
    def scheduleHeatbeatForProducer(self):
        """生产者的blockconnection保持连接
        """
        # logging.info('sending heartbeat for producer')
        # 仅当消费者启动时才周期性发送生产者的保持连接请求. 独立使用生产者时无法运行.
        if not self._consuming:
            logging.info('consumer stopped, cancel producer heartbeat')
            return
        self._producer.connection.process_data_events()
        self._connection.ioloop.call_later(5, self.scheduleHeatbeatForProducer)
    
    def close(self):
        """关闭所有连接
        """
        if self._producer:
            self._producer.close()
        if self._connection:
            self.closeConnection()