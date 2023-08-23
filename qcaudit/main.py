# #!/usr/bin/env python3

# """ The hospqc main entry
# """

# import logging
# import os
# import time
# from concurrent import futures
# # mysql密码中存在@时，通过url连接可能抛异常
# from urllib.parse import quote_plus
# from pymongo.uri_parser import parse_uri

# from argparse import ArgumentParser
# from qcaudit.app import Application
# from iyouframework.env import GetArgumentParserVariableFlagSetterByFlag
# from iyouframework.grpc import ServerInsecureInterceptor, ServerOpenAPIProtectionInterceptor
# from qcaudit.service.auditservice import AuditService
# from qcaudit.service.doctor_service import DoctorService
# from qcaudit.service.qcitems_service import QCItemsServer
# from qcaudit.service.sampleservice import SampleServicer
# from qcaudit.service.qccdss_service import QCCDSSManagerServicer

# # import grpc
# # from iyouframework.grpc import ClientOpenAPIProtectionInterceptor

# from qcaudit.context import Context
# from qcaudit.service.stats_service import StatsService

# DefaultFlagVarsPath = "/var/run/rxthinking.com/hospqc/flags"

# logger = logging.getLogger('hospqc')
# DefaultTimeout = 120.0  # 90s
# DefaultMongodbDatabase = "iam"


# def getArguments():
#     """ Get arguments
#     """
#     # Get flag setter
#     flagSetter = GetArgumentParserVariableFlagSetterByFlag("--flag-vars-path", DefaultFlagVarsPath, writeLog=True)
#     parser = ArgumentParser(description="hospqc micro service")
#     parser.add_argument("--debug", dest="debug", default=flagSetter.getDefault("debug", False), action="store_true",
#                         help="Enable debug")
#     parser.add_argument("--host", dest="host", default=flagSetter.getDefault("host", "127.0.0.1"),
#                         help="The binding host")
#     parser.add_argument("--port", dest="port", type=int, default=flagSetter.getDefault("port", 6024),
#                         help="The binding port")
#     parser.add_argument("--flag-vars-path", dest="flagVarsPath", default=DefaultFlagVarsPath,
#                         help="The path of flag vars")
#     parser.add_argument("--disable-access-control", dest="disableAccessControl", action="store_true",
#                         default=flagSetter.getDefault("disable-access-control"), help="Disable access control")
#     parser.add_argument("--db-host", dest="dbHost", default=flagSetter.getDefault("db-host"), help="The database host")
#     parser.add_argument("--db-port", dest="dbPort", type=int, default=flagSetter.getDefault("db-port"),
#                         help="The database port")
#     parser.add_argument("--db-database", dest="dbDatabase", default=flagSetter.getDefault("db-database"),
#                         help="The database name")
#     parser.add_argument("--db-uname", dest="dbUsername", default=flagSetter.getDefault("db-uname"),
#                         help="The database username")
#     parser.add_argument("--db-password", dest="dbPassword", default=flagSetter.getDefault("db-password"),
#                         help="The database password")
#     parser.add_argument("--mongodb-uri", dest="mongodbURI", default=flagSetter.getDefault("mongodb-uri"),
#                         help="The mongodb uri")
#     parser.add_argument("--iam-database", dest="iamDatabase", default=flagSetter.getDefault("iam-database", "iam"),
#                         help="The iam mongodb database name")
#     parser.add_argument("--emr-addr", dest="emrAddr", default=flagSetter.getDefault("emr-addr"), help="emr接口地址")
#     parser.add_argument("--ai-url", dest="aiUrl", default=flagSetter.getDefault("ai-url"), help="ai质控接口地址")
#     parser.add_argument("--mq-url", dest="mqUrl", default=flagSetter.getDefault("mq-url"), help="消息队列amqp url")
#     parser.add_argument("--rpc-addr", dest="rpcAddr", default=flagSetter.getDefault("rpc-addr"), help="消息推送地址")
#     parser.add_argument("--emr-adapter", dest="emrAdapter", default=flagSetter.getDefault("emrAdapter"), help="emr接口适配器服务地址")
#     parser.add_argument("--qcetl-rpc", dest="qcetlRpc", default=flagSetter.getDefault("qcetlRpc"), help="qcetl-rpc 消息地址")
#     parser.add_argument("--ai-cache-api", dest="aiCacheApi", default=flagSetter.getDefault("aiCacheApi"), help="ai缓存文书内容接口")
#     parser.add_argument("--cdss-addr", dest="cdssAddr", default=flagSetter.getDefault("cdss-addr"), help="cdss地址")
#     parser.add_argument("--redis-addr", dest="redisAddr", default=flagSetter.getDefault("redis-addr"), help="redis地址")
#     parser.add_argument("--migrate", dest="migrate", default=flagSetter.getDefault("debug", False), action="store_true",
#                         help="是否根据 qcmigration 自动迁移数据库表结构")
#     parser.add_argument("--task", dest="task", default=flagSetter.getDefault("task", False), action="store_true", help="是否为启动抽取定时任务进程")
#     # Done
#     return parser.parse_args()


# def main(ContextClass=None, ServiceClasses=None):
#     """The main entry
#     """
#     args = getArguments()
#     # Set logging
#     if args.debug:
#         logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', level=logging.DEBUG)
#     else:
#         logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', level=logging.INFO)
#     logger = logging.getLogger('hospqc.server')

#     # create mysql config
#     if not args.dbHost:
#         raise ValueError("Require mysql db host")
#     dbConfig = {
#         'host': args.dbHost or 'localhost',
#         'port': args.dbPort or 3306,
#         'user': args.dbUsername or 'root',
#         'passwd': quote_plus(args.dbPassword or ''),
#         'database': args.dbDatabase or "qcmanager",
#         'charset': 'utf8mb4',
#     }
#     mysqlUrl = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}?charset={charset}".format(**dbConfig)
#     logging.info("mysqlUrl, %s", mysqlUrl)
#     emrAddr = args.emrAddr
#     emrAdapterUrl = args.emrAdapter or ""

#     # Create mongodb
#     if not args.mongodbURI:
#         raise ValueError("Require mongodb uri")
#     if not args.iamDatabase:
#         mongodbURI = parse_uri(args.mongodbURI)
#         mongo_db = mongodbURI.get("database")
#         if not mongo_db:
#             mongo_db = "iam"
#     else:
#         mongo_db = args.iamDatabase

#     # start server
#     server = grpc.server(futures.ThreadPoolExecutor(max_workers=50))
#     if args.disableAccessControl:
#         interceptor = ServerInsecureInterceptor(True)
#     else:
#         interceptor = ServerOpenAPIProtectionInterceptor(True)
#     app = Application(mysqlUrl, args.mongodbURI, mqUrl=args.mqUrl, iamDatabase=args.iamDatabase,
#                       emrAdapterUrl=emrAdapterUrl, qcetlRpcUrl=args.qcetlRpc, aiCacheApi=args.aiCacheApi,
#                       cdssAddr=args.cdssAddr, redisAddr=args.redisAddr, migrate=args.migrate)
#     if args.task:
#         from qcaudit.task import TaskServer
#         task_server = TaskServer(app)
#         task_server.runTask()
#     if not ContextClass:
#         context = Context(app)
#     else:
#         context = ContextClass(app)

#     if not ServiceClasses:
#         AuditService.addToServer(AuditService(context), server, interceptor)
#         SampleServicer.addToServer(SampleServicer(context), server, interceptor)
#         StatsService.addToServer(StatsService(context), server, interceptor)
#         DoctorService.addToServer(DoctorService(context), server, interceptor)
#         QCItemsServer.addToServer(QCItemsServer(context), server, interceptor)
#         QCCDSSManagerServicer.addToServer(QCCDSSManagerServicer(context), server, interceptor)
#     else:
#         for ServiceClass in ServiceClasses:
#             ServiceClass.addToServer(ServiceClass(context), server, interceptor)

#     server.add_insecure_port("%s:%d" % (args.host, args.port))
#     logging.info("Start gRPC insecure server at %s:%d", args.host, args.port)
#     server.start()
#     try:
#         while True:
#             time.sleep(3600)
#     except KeyboardInterrupt:
#         server.stop(0)
#     logging.info("gRPC server stopped")


