#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   __init__.py
@Time    :   2023/05/29 13:27:01
@Author  :   zhangda 
@Desc    :   None
'''


import os
from pymongo.uri_parser import parse_uri


db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('DB_USER')
db_pw = os.getenv('DB_PW')
db_db = os.getenv('DB_DATABASE', 'qcamanager')
debug_flag = os.getenv('DEBUG')
disableAccessControl = os.getenv('DisableAccessControl')
emrAddr = os.getenv('emrAddr')
mongodbURI = os.getenv('mongodbURI')
iamDatabase = os.getenv('iamDatabase')  # mongo
bigdataDatabase = os.getenv('bigdataDatabase')  # mongo
mqUrl = os.getenv('mqUrl')
aiUrl = os.getenv('aiUrl')
rpcAddr = os.getenv('rpcAddr')
emrAdapterUrl = os.getenv('emrAdapter')
qcetlRpc = os.getenv('qcetlRpc')
aiCacheApi = os.getenv('aiCacheApi')
cdssAddr = os.getenv('cdssAddr')
redisAddr = os.getenv('redisAddr')
migrate = os.getenv('migrate')
task = os.getenv('task')


dbConfig = {
    'host': db_host,
    'port': db_port,
    'user': db_user,
    'passwd': db_pw,
    'database': db_db,
    'charset': 'utf8',
}
mysqlUrl = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{database}?charset={charset}".format(**dbConfig)

# Create mongodb
if not mongodbURI:
    raise ValueError("Require mongodb uri")
if not iamDatabase:
    mongodbURI = parse_uri(mongodbURI)
    database = mongodbURI.get("database")
    if not database:
        database = "iam"
else:
    database = iamDatabase


