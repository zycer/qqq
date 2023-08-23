#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: download_doc_dept.py
@time: 2022/4/27 15:34
@desc:
"""
import logging
import time

import streamlit as st
import json
from argparse import ArgumentParser

from sqlalchemy import func

from .qcdatabase import QCDataBaseManager


logger = logging.getLogger(__name__)


def getArgs():
    parser = ArgumentParser(prog='结构化标准文书导出-科室', description='### 结构化标准文书导出-科室')
    parser.add_argument('--db-host', dest='dbHost', default="mysql.infra-default", help='数据库HOST')
    parser.add_argument('--db-port', dest='dbPort', default="3306", help='数据库PORT')
    parser.add_argument('--db-db', dest='dbDb', default="qcmanager", help='数据库DB')
    parser.add_argument('--dept-max', dest='deptMax', default=3, help='科室提取文书数', choices=[1, 2, 3])
    parser.add_argument('--doc-max', dest='docMax', default=50, help='导出标准文书数', type=int)
    return parser


def process(args):
    start_time = time.time()
    db_url = 'mysql+pymysql://root:rxthinkingmysql@{h}:{p}/{d}?charset=utf8mb4'.format(h=args.dbHost, p=args.dbPort, d=args.dbDb)
    db = QCDataBaseManager(db_url)
    doc_data = []
    with db.session() as s:
        emr_info = db.models["emrInfo"]
        emr_content = db.models["emrContent"]
        query_normal = s.query(db.models["documents"]).all()
        normal_dict = {item.name: item.standard_name for item in query_normal}
        res = s.query(func.max(emr_info.id).label("c")).first()
        info_max_id = res.c
        dept_data = {}
        start = 500
        end = 0
        while len(doc_data) < args.docMax:
            min_id = info_max_id - start
            max_id = info_max_id - end
            query = s.query(emr_info, emr_content).join(emr_content, emr_info.emrContentId == emr_content.id).filter(emr_info.department != "", emr_info.department.isnot(None), emr_info.id >= min_id, emr_info.id <= max_id)
            start += 500
            end += 500
            queryset = query.all()
            for info, content in queryset:
                if not info.department:
                    continue
                dept_doc_data = dept_data.get(info.department or "", [])
                if not dept_doc_data:
                    dept_data[info.department] = []
                if len(dept_doc_data) < args.deptMax:
                    create_time = info.createTime.strftime("%Y-%m-%d %H:%M:%S") if info.createTime else ""
                    record_time = info.recordTime.strftime("%Y-%m-%d %H:%M:%S") if info.recordTime else ""
                    tmp = {"caseId": info.caseId, "docId": info.docId, "documentName": info.documentName.strip(),
                           "contents": content.contents, "normalName": normal_dict.get(info.documentName.strip(), info.documentName.strip()),
                           "htmlContent": content.htmlContent, "createTime": create_time, "recordTime": record_time}
                    dept_data[info.department].append(tmp)
                    if len(doc_data) <= args.docMax:
                        doc_data.append(tmp)
    with open("/tmp/doc_dept.txt", "wb") as f:
        for item in doc_data:
            f.write(json.dumps(item, ensure_ascii=False).encode())
            f.write(b"\n")
    with open("/tmp/doc_dept.txt", "rb") as f:
        data = f.read()
    st.download_button('下载', data=data, file_name='结构化文书.txt', help='点击下载')
    end_time = time.time()
    logger.info("end, use: %s", end_time - start_time)
    return ""


# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getArgs()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process

