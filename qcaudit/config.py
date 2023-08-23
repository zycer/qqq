#!/usr/bin/env python3
import json
import logging
from collections import namedtuple
from typing import Dict, List
import yaml
import os

ConfigItem = namedtuple('ConfigItem', ('name', 'value', 'scope', 'platform'))
class Config(object):
    # yaml 文件地址
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

    # 初审审核通过时是否通知emr
    QC_APPROVE_NOTIFY_EMR_FIRST = 'qc.{auditType}.approve.notifyEmr.first'
    # 终审审核通过时是否通知emr
    QC_APPROVE_NOTIFY_EMR_FINAL = 'qc.{auditType}.approve.notifyEmr.final'
    # 初审审核不通过时是否通知emr
    QC_REFUSE_NOTIFY_EMR_FIRST = 'qc.{auditType}.refuse.notifyEmr.first'
    # 终审审核不通过时是否通知emr, 若不通知则通过和不通过是一样的,就是完成质控
    QC_REFUSE_NOTIFY_EMR_FINAL = 'qc.{auditType}.refuse.notifyEmr.final'
    # 审核通过是否清除问题
    QC_APPROVE_CLEAR_PROBLEM_FIRST = 'qc.{auditType}.approve.clearProblem.first'
    QC_APPROVE_CLEAR_PROBLEM_FINAL = 'qc.{auditType}.approve.clearProblem.final'
    # 在哪些状态允许退回, 是一个逗号分隔字符串
    QC_REFUSE_ALLOWED_STATUS = 'qc.{auditType}.refuse.allowedStatus'

    # 是否开启抽取
    QC_SAMPLE_STATUS = 'qc.{auditType}.extract'
    # 归档环节配置
    QC_ARCHIVE_STEP = 'qc.archived.step'
    # 院级病案得分计算规则覆盖环节
    QC_ARCHIVESCORE_OVERWRITE_STEP = 'qc.archiveScore.overwrite.step'
    # 是否有终审环节
    QC_FINAL_STATUS = 'qc.{auditType}.final'  # 1 需要，2 不需要

    # 查询病例时是否需要流程控制病例的展示
    QC_PRECONDITION = "qc.{auditType}.precondition"

    # 查询时是否过滤 已出院未申请状态病历
    QC_NOT_APPLY_AUDIT = "qc.{auditType}.case.notapply.audit"

    # 文书列表排序设置 1=目录，2=文书书写时间
    QC_EMR_SORT = 'qc.emr.sort'

    # 终末病历规则组
    QC_GROUP_ARCHIVE = 'qc.group.{auditType}.archive'

    # 病历号/病案号
    QC_PATIENT_ID_NAME = 'qc.patientId.name'

    # 分配纬度, 1-科室, 2-病区
    QC_ASSIGN_DIMENSION = "qc.assign.dimension"

    # 质控/审核通过时是否通知
    QC_FINISH_NOTIFY_DOCTOR = "qc.{auditType}.finish.notify.doctor"

    # 统计级别显示方式, 甲级,乙级,丙级/优秀,合格,不合格
    QC_STATS_LEVEL = "qc.stats.level"
    # 医生端待提交列表查询患者类型, 1-门诊, 2-住院, 3-急诊, None-全部
    QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE = "qc.doctor.waitApply.patientType"
    # 医生端低于90分病历是否可以提交强控, 1-可以提交, 2-不可以
    QC_DOCTOR_VETO = "qc.doctor.veto"

    # 质控评分表模板名称
    QC_SCORE_REPORT_TEMPLATE = "qc.score.report.template"

    # 医生端ip黑名单全局开关
    QC_DOCTOR_BLOCKIP_ALL = "qc.doctor.blockip.all"
    QC_DOCTOR_SWITCH = "qc.doctor.switch"

    # 系统第一次正式上线的日期
    QC_FIRST_ONLINE_PUBLISH_TIMESTAMP = "qc.1st.online.publish.timestamp"
    # 科室归档率明细列表是否需要科室汇总行数据
    QC_STATS_DEPT_ARCHIVE = "qc.stats.dept.archive"

    # 病历质控病历列表筛选是否需要诊疗组字段, 1-需要
    QC_CASE_GROUP_FLAG = "qc.case.group.flag"
    # 病历质控归档病历质量统计是否抽查
    QC_STATS_ARCHIVED_SAMPLE = "qc.stats.archived.sample"
    # 医院名
    HOSPITAL_NAME = "hospital.name"

    # 是否允许抽取归档
    QC_SAMPLE_ARCHIVE = 'qc.{auditType}.sample.archive'
    # 指标分析-全院、科室、医生病案指标展示列
    QC_STATS_BRANCH_TARGET_FIELD = "qc.stats.branch.target.field"

    # 查询是否确认签收状态的外部地址
    QC_AUDIT_ONLY_RECEIVED = "qc.{auditType}.only.received"

    # 审核页面左侧文书目录使用哪个字段做对照
    QC_DOCUMENT_CATALOG_FIELD = "qc.document.catalog.field"
    # 质控完成节点
    QC_COMPLETE_AUDIT_TYPE =  "qc.complete.auditType"

    # 运行病历抽取和事中质控是否显示重点病历标签相关的内容，1=是，2=否
    QC_ACTIVE_TAGS = "qc.active.tags"

    def __init__(self, connection):
        self._configItems: Dict[tuple, ConfigItem] = {}
        self.connection = connection
        self.configItems = []
        self.load()
    
    @property
    def items(self):
        return self._configItems.values()

    @property
    def itemList(self):
        return self.configItems

    def load(self):
        print(self.PATH)
        model = self.connection['configItem']
        configs = self.getConfigList()
        config_dict = {config.name: config for config in configs}
        with open(self.PATH, 'r', encoding="utf-8") as f:
            config_yml = yaml.full_load(f.read())
        with self.connection.session() as session:
            for key, item in config_yml.items():
                conf = config_dict.get(key)
                if not conf:
                    _choice = dict()
                    choices = item.get('choice', list())
                    if choices:
                        _choice = {choice['label']: choice['value'] for choice in choices}
                    default_value = item.get('default_value', '')
                    if item['type'] == 'radio':
                        default_value = _choice.get(default_value, '')
                    if item['type'] == 'multi':
                        values = default_value.split(',')
                        default_value = ','.join([_choice.get(val, '') for val in values])
                    conf_item = model(
                        name=key,
                        name_ch=item.get('name', ''),
                        value=default_value,
                        default_value=item.get('default_value', ''),
                        type=item.get('type', ''),
                        choice='|'.join([json.dumps(choice, ensure_ascii=False) for choice in choices]) if choices else '',
                        scope=item.get('scope', None),
                        message=item.get('message', '')
                    )
                    session.add(conf_item)
        self.reload()

    def reload(self):
        model = self.connection['configItem']
        tmp = []
        self.configItems = []
        with self.connection.session() as session:
            for row in session.query(model):
                tmp.append(
                    ConfigItem(name=row.name, value=row.value, scope=row.scope, platform=row.platform)
                )
                self.configItems.append(ConfigItem(name=row.name, value=row.value, scope=row.scope, platform=row.platform))

        self._configItems = {
            item.name: item.value for item in tmp
        }
    
    def get(self, name, platform=None, scope=None, default=None):
        return self._configItems.get(name)

    def set(self, name, value, platform=None, scope=None):
        """设置配置项
        """
        model = self.connection['configItem']
        with self.connection.session() as session:
            item = session.query(model).filter(model.name == name).first()
            if item:
                item.value = value
            else:
                session.add(model(name=name, value=value, platform=platform, scope=scope))
                session.commit()
        # 更新缓存
        # self.reload()
        exist = False
        for i in range(len(self.configItems)):
            if self.configItems[i].name == name:
                exist = True
                self.configItems[i] = ConfigItem(name=name, value=value, scope=scope, platform=platform)
        if not exist:
            self.configItems.append(ConfigItem(name=name, value=value, scope=scope, platform=platform))
        self._configItems[name] = value
        print(f'修改配置项 {name}: {self.get(name)}')

    def isSampleEnabled(self, auditType):
        """检查此审核环节是否打开了抽样

        Args:
            auditType ([type]): 审核类型
        """
        return True
    
    def refuseAllowedStatus(self, auditType):
        """
            各个环节允许退回的状态
        Args:
            auditType ([type]): [description]

        Returns:
            [type]: [description]
        """
        value = self.get(self.QC_REFUSE_ALLOWED_STATUS.format(auditType=auditType))
        if not value:
            return []
        else:
            # return [int(item) for item in value.split(',')]
            return [1, 3, 5, 7]

    def getConfigList(self, request=None):
        model = self.connection['configItem']
        result = list()
        with self.connection.session() as session:
            query = session.query(model)
            if request:
                if request.input:
                    query = query.filter(model.name_ch.like('%%%s%%' % request.input))
                if request.scope:
                    query = query.filter(model.scope.like('%%%s%%' % request.scope))
            for item in query.all():
                session.expunge(item)
                result.append(item)
            return result

    def getArchiveSteps(self):
        """归档环节
        """
        options = {
            '1': "",
            '2': "department",
            '3': "hospital",
            '4': "firstpage",
            '5': "expert"
        }
        values = self.get(self.QC_ARCHIVE_STEP).split(',')
        return [options.get(item) for item in values if options.get(item)]
