#!/usr/bin/env python3
from qcaudit.config import Config
from qcaudit.infra.rabbitmq import RabbitMQ
from sqlalchemylib.sqlalchemylib.connection import Connection
from qcdbmodel.qcdbmodel.models import QCAUDIT_TABLES
from pymongo import MongoClient
from redis import ConnectionPool
from rabbitmqlib.rabbitmqlib.producer import ThreadSafeBlockingProducer


class Application(object):
    """grpc application

    """

    def __init__(self, mysqlUrl, mongoUrl, mqUrl="", iamDatabase="iam", emrAdapterUrl=None, qcetlRpcUrl=None,
                 aiCacheApi=None, cdssAddr=None, redisAddr=None, migrate=None):
        self.mysqlConnection = Connection(mysqlUrl, createIfNotExists=True, declareTables=QCAUDIT_TABLES, automigrate=migrate)
        # mongodb数据库连接
        self.mongo = MongoClient(mongoUrl)
        # 导出服务
        self.exportService = None
        # 字典服务
        self.dictService = None
        # iam
        self.iamService = None
        # 配置信息, 需要从数据库读取
        self.config = Config(self.mysqlConnection)
        # rabbitmq
        if mqUrl:
            self.mq = RabbitMQ(mqUrl)
            self.producer = ThreadSafeBlockingProducer(mqUrl)
        self.iamDatabase = iamDatabase
        self.qcetlRpcUrl = qcetlRpcUrl
        self.aiCacheApi = aiCacheApi
        self.emrAdapterClient = None
        self.emrAdapterUrl = emrAdapterUrl
        self.cdssAddr = cdssAddr
        self.redisAddr = redisAddr
        self.redis_pool = None
        if self.redisAddr:
            self.redis_pool = ConnectionPool.from_url(self.redisAddr)
    #     self.initExternalServices(emrAdapterUrl)

    # def initExternalServices(self, emrAdapterUrl=None):
    #     """初始化外部服务, grpc stub等
    #     """
    #     if emrAdapterUrl:
    #         channel = grpc.insecure_channel(emrAdapterUrl, options=[
    #             ('grpc.client_idle_timeout_ms', 600000),
    #         ])
    #         interceptor = ClientOpenAPIProtectionInterceptor()
    #         emrAdapterClient = EmrAdapterStub(channel, interceptor)
    #         self.emrAdapterClient = emrAdapterClient

    # def run(self, host, port):
    #     raise NotImplementedError()
