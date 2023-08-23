# rabbitmqlib

封装一些rabbitmq连接操作

![消费者处理流程](consumer.jpg)
![生产者处理流程](producer.jpg)

### 功能特点

* 封装消费者处理逻辑, 只需要提供一个callback函数实现一个消费者.
* 支持消费者缓存消息批量处理(通过callback函数的返回值实现)
* 支持消息处理失败自动重试
* 支持延迟发送消息(固定时间)
* 支持消息去重, 近期处理过的消息不再处理, 需要redis支持
* 支持定时发送消息(未来任意时间), 需要redis支持
* 支持记录消息接收和发送日志(需要rabbitmqlog服务将日志记录到mongodb)

# 使用方法

## 数据类型

### Message (消息结构体)

* Exchange/RoutingKey: 只在接收到的消息中存在, 自动设置
* MessageId: 消息的id,  在消息初始化的时候会自动基于uuid生成, 接收到的消息如果是基于rabbitmqlib实现的则已经带上id, 若不是基于rabbitmqlib则会自动分配一个id
* Type: 消息的类型. 一般情况下和routing_key相同
* Timestamp: 消息的创建时间, 通过rabbitmqlib发送的消息会自动带上此属性. 对于其他渠道发送的消息但是通过rabbitmqlib消费的, 此属性和ReceiveTime一致
* ReceiveTime: 消息的接收时间, 在消息接收时自动设置
* Failed: 消息是否处理失败, 需要通过markFailed()函数设置
* ParentId: 父消息id, 记录当前消息是处理哪个消息时生成的. 需要通过setParentId()来设置.
* RedeliveredCount: 消息被重试的次数, 在消息处理失败retry时会自动设置
* 其他设置在properties中的属性
  * priority: 消息的优先级, 暂时没什么用
  * expiration: 消息的超时时间, 也就是消息的ttl, 当消息超时后会自动发送到死信交换机.  主要在往延迟队列中发送时设置.
  * correlation_id: 对于需要回复的消息使用
  * reply_to: 对于需要回复的消息使用, 要回复到的队列

### MessageResult (消息的处理结果)

* success: 处理成功或失败,  bool型
* result: 处理的结果, 任意类型
* nextMessage: 某些消息在处理完成后会生成一个新的消息, 虽然这个消息没有被发送到rabbitmq中, 但是也是同样的结构.

### ReplyMessage (回复消息)

对于需要回复的消息的响应消息

* code: 返回代码. 目前并没有定义标准值
* message: 错误消息
* body: 响应体

### RabbitMqManager

## 启动消费者服务

1. 初始化rabbitmq连接

* 可指定logExchange和logRoutingKey两个参数, 指定后会将消息的发送和处理日志再次发送到rabbitmq, 另一个服务rabbitmqlog会将日志写入到mongodb, 并提供可视化工具. 参考http://git.bdmd.com/server/bigdata/rabbitmqlog

```python
from rabbitmqlib.rabbitmqlib import RabbitMqManager

# 还可指定logExchange,logRoutingKey这两个参数, 若指定则会将消息的发送接收处理日志发送到rabbitmq中, 可通过rabbitmqlog服务对日志进行收集和查看.
manager = RabbitMqManager("amqp://rxthinking:gniknihtxr@192.168.101.155:42158/%2F")

```

3. 增加要监听的队列, 并定义队列消息回调函数

```python
def callback(message: Message) -> MessageResult:
    """这是一个默认消息处理函数, 他仅仅是打日志"""
    logging.info(message.Body)
    return MessageResult(True)

# 监听一个队列, 使用callback函数作为消息处理函数. 
# 可以通过retryTimes设置消息处理失败的重试次数, 还可以设置重试间隔
# 当超出重试次数后消息会被发往死信交换机
manager.listen(name='qc.search.1', exchange='qcetl', callback=callback, deadExchange='qcetl.dead', retryTimes=3)
```

3. 启动监听程序

```python
# 可以手动ctrl+c退出, 当连接中断时会自动重连
mananger.run()
# 在后台启动, 不影响主线程服务
mananger.runAsync()
```

### 特殊功能

listen函数的一些特殊参数说明如下:

* autoDelete: 消费者下线后自动删除.
* exclusive: 排他队列, 创建的队列只有当前消费者可以消费, 一般情况下要和autoDelete配合使用, 因为在k8s启动的消费者每次名称都不一样, 不设置autoDelete下次会无法消费.
* interval: 消息距上次处理的最小间隔, 用来防止重复消息频率过高. 当RabbitMqManager初始化指定redisUrl时可用.
* flush_interval: 消息刷新间隔. 当此参数大于0, 且RabbitMqManager的prefetchCount设置的大于1时, 消息将被批量处理. 此时注意callback函数需要实现刷新缓存的功能.
  * callback的返回值说明

    * 若result is None, 表示callback并没有处理消息, 而是将消息缓存了, 此时框架会在flush_interval秒的时间通知callback需要将缓存全部处理完. 通知的方法是用None作为参数调用callback.  此时callback应当将所有缓存下来的消息全部处理完毕, 并返回MessageResult. 此时不允许callback再返回None了.
    * 若result.success为True表示所有消息均处理成功, 消息将被全部ack
    * 若result.success为False, 无论是否有消息处理成功, 全部当做处理失败, 全部reject(没有超出最大重试次数的会被重试)
  * 注意flush_interval一定要小于prefetchCount条消息处理需要的时间, 否则无法达到批量处理效果, 反而可能会导致消费者一致在等待消息
  * flush_interval>0时interval参数无效, 因为可能存在消息被缓存的情况, 处理时间间隔会比较复杂.
  * flush_interval>0时消息无法回复, 因为同一批消息的只有一个result.
* threaded:   将消息处理的callback放到另一个线程中执行.   这是由于运行时间过长的任务会导致pika与server端丢失心跳, 当指定threaded=True时, 会将callback放在独立线程运行, 并在主线程处理心跳事件, 以保证连接不会中断.
  * 注意: 创建线程是有开销的, 如果任务执行时间很短, 就不要使用此参数. 默认情况下超过120s才会失去心跳, 所以只有任务最长需要120s以上才有必要设置.

## 如何发送消息

1. 若只需要发送消息而不需要消费消息, 那么直接创建manager对象,并调用manager.send()发送消息即可
2. 若需要在消费的过程中发送消息, 应该定义一个处理类,将mananger传进去

   ```python
   class MessageHandler:
       def __init__(self, manager: RabbitMqManager):
           self.manager = manager

       def onMessage(self, message: Message):
           """消息处理函数"""
           try:
               # 对消息进行处理, 得到处理结果
               result = MessageResult(True)
               manager.send(Message(body={"xxx": "xxx"}, parentId=message.MessageId), exchange='要发送的exchange', 
                                      routingKey='要发送的routingKey', delay=60000)
           except Exception as e:
               logging.exception(e)
               return MessageResult(False)
   handler = MessageHandler(manager)
   manager.listen(name='队列名称', exchange='exchange', routingKey='routingKey', callback=handler.onMessage)
   ```
3. 预约一个未来的时间发送消息.

   * 预约发送消息依赖redis, 需要在manager初始化时指定redisUrl
   * 预约发送的消息需要有一个服务启动调度器, 来将redis中到期的消息取出发送到mq中. 为防止调度器产生争抢, 对于同一个schedulerRedisKey全局只能启动一个取消息服务. 一般情况下使用默认的schedulerRedisKey并在rabbitmqlog这个服务中启动调度器即可.

```python
# 定时发送消息使用redis实现, 需要指定redisUrl
manager = RabbitMqManager("amqp://rxthinking:gniknihtxr@192.168.101.155:42158/%2F", redisUrl='redis://192.168.101.155:6379/0', schedulerRedisKey='qcetl')
# 发送定时消息, dueTime是计划发送时间
manager.send(Message(body={'xx': 'xx'}), exchange='qcetl', routingKey='test', dueTime=datetime.strftime('2022-02-03 00:00:00', '%Y-%m-%d %H:%M:%S'))
# 启动调度器, 如果此服务专门用于启动调度器, 可使用block=True, 否则可以指定block=False, 在用manager.run()启动.
manager.startScheduler(block=True)
```

4. 延迟发送消息.  不想消息立刻被消费者处理到, 可以在调用manager.send时增加参数delay=毫秒数,  消息将会先放到延迟队列, 超时后才会被放入实际队列.   注意延迟发送消息要保证同一个延迟交换机收到的消息延迟时间都一样, 否则有可能会导致队列被堵塞.

## 日志记录

当RabbitMqManager初始化时指定了logExchange和logRoutingKey两个参数时, 会使用message.asLog()生成日志并再次发送到rabbitmq中. rabbitmqlog服务会收集日志并写入mongodb, 默认情况下日志保存180天.为保证日志信息完整度, 最好服从以下约定

* 在处理消息的过程中发送出去的消息,  要使用setParentId设置父消息的id
* 所有的消息服务都基于本项目来实现, 否则消息id和时间戳均无法准确记录
* 消息处理失败时不要手动重试消息, 而是通过在addQueueProcessor的时候指定retryTimes来自动重试. 这样会完整保留重试历史.

```python
manager =  RabbitMqManager("amqp://rxthinking:gniknihtxr@192.168.101.155:42158/%2F", logExchange='qcetllog', logRoutingKey='qcetllog')
```
