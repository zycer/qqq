#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-05-15 13:54:15

'''
from datetime import datetime
from typing import Iterable, Tuple
from redis import ConnectionPool, Redis
from .message import Message
import arrow
import logging
import sys
import time


class MessageScheduler:
    """某一些消息希望在指定时间被消费, rabbitmqlib的消息ttl实现不了这一点.
    因为rabbitmqmq并没有对消息按照ttl进行排序, 而是只判断队首的消息有没有超过ttl,队首消息没有到达ttl, 其后面的消息无法被消费,这种情况下如果队首消息的ttl是无穷大就会导致整个队列被阻塞用于不会被消费.

    解决方案是引入redis, 通过redis中的sortedset来实现.
    1. 发送定时消息时使用计划发送时间的时间戳作为sortedset的score. 将消息写入redis.
    2. 使用一个定时任务轮询redis, 当发现redis中分数最小的那个消息的时间戳已经超过当前时间, 则将其发送到rabbitmq. 

    注: 由于轮询频率不会特别高, 因此实际消息发送时间会有误差, 不建议借用此功能来实现很精准的定时消息(5秒以内)
    """
    DEFAULT_KEY = '_rabbitmqlib_scheduler'

    def __init__(self, redisUrl: str, redisKey='_rabbitmqlib_scheduler'):
        self.pool = ConnectionPool.from_url(redisUrl)
        # 调度器在redis中存储的key
        self.redisKey = redisKey
        
    def isDuplicateMessage(self, message: Message, interval=60) -> bool:
        """获取消息上次被处理的时间

        Args:
            message (Message): 
            interval (int): 两次处理的最大间隔
        
        Returns:
            bool: 上次处理时间是否超过间隔
        """
        key = message.getHash()
        with Redis(connection_pool=self.pool) as conn:
            value = conn.get(key)
            lastReceivedTime = int(value) if value else 0
            
            currTime = int(time.time())
            # 如果已经超过设置的间隔, 那么更新时间戳
            if currTime - lastReceivedTime > interval:
                conn.set(
                    key, str(currTime),
                    ex=interval*5
                )
                return False
            else:
                return True

    def schedueByTime(self, message: Message, exchange: str,
                      routingKey: str, dueTime: datetime):
        """预约于计划时间发送消息

        Args:
            message (Message): 要发送的消息
            exchange (str): 消息计划发送到的exchange
            routingKey (str): 消息计划发送到的routingkey
            dueTime (datetime): 计划发送时间. 如果相同消息已经预约过, 将会覆盖其发送时间, 不会重复发送. 若要实现周期性发送消息, 请在消息被发送后再预约下一次.
        """
        # 未指定时区的时间都当做+08:00区时间
        # 获取utc时间戳
        if dueTime.tzinfo is None:
            score = arrow.get(dueTime, 'Asia/ShangHai').timestamp
        else:
            score = arrow.get(dueTime).timestamp

        # 消息dump成字符串
        messageStr = message.marshal(exchange=exchange, routingKey=routingKey)

        logging.info("%s is due to sent at %s", message.Body,
                     dueTime.strftime('%Y-%m-%d %H:%M:%S'))
        try:
            with Redis(connection_pool=self.pool) as conn:
                conn.zadd(self.redisKey, {
                    messageStr: score
                })
        except Exception as e:
            logging.exception(e)
            logging.error('schedule message failed, %s', message.Body)

    def fetchExpiredMessages(self) -> Iterable[Tuple[Message, str, str]]:
        """获取预约到期的消息

        Returns:
            Iterable[Tuple[Message, str, str]]: Message, exchange, routingKey
        """
        nowTime = arrow.utcnow().to('+08:00')
        currentTimestamp = nowTime.timestamp
        with Redis(connection_pool=self.pool) as conn:
            while True:
                # 取出最早要执行的消息
                result = conn.zrangebyscore(
                    self.redisKey,
                    0, sys.maxsize,
                    start=0, num=1, withscores=True
                )
                if not result:
                    logging.info('no message found from redis')
                    break
                value, score = result[0]
                if not value:
                    # 消息内容为空, 跳过
                    logging.info("message from redis is empty, skipping")
                    conn.zrem(self.redisKey, value)
                    continue

                # 如果到了执行时间, 从redis中删除消息并返回
                # 由于不是原子操作, 如果启动了多个调度器, 这个地方有可能会删除失败, 如果删除失败表示已经被其他的调度器移除, 则不需要发送消息
                if score < currentTimestamp:
                    ret = conn.zrem(self.redisKey, value)
                    if ret == 0:
                        logging.info('message not exists, maybe removed by other scheduler. %s', value)
                        continue
                    message, exchange, routingKey = Message.unMarshal(value)
                    logging.info('found message: %s, due time: %s, will send to %s:%s',
                                 message.Body[:256], arrow.get(score).to("+08:00"), exchange, routingKey)
                    yield (message, exchange, routingKey)
                else:
                    logging.info("message is dued at %s, stoping",
                                 arrow.get(score).to("+08:00"))
                    break
    