# coding: utf-8
"""
病种控费相关的表结构

"""
from sqlalchemy import Column, DateTime, Float, String, Text, text
from sqlalchemy.dialects.mysql import INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class FeeMajor(Base):
    __tablename__ = 'feeMajor'

    id = Column(INTEGER(11), primary_key=True)
    diseaseMajor = Column(String(255), comment='病种分类')
    status = Column(INTEGER(11), server_default='1', comment='状态 0停用 1在用')


class FeeManager(Base):
    __tablename__ = 'feeManager'

    id = Column(INTEGER(11), primary_key=True)
    diseaseName = Column(String(255), comment='病种名称')
    type = Column(String(255), comment='分类')
    mainTreatment = Column(String(255), comment='主要治疗方式')
    diseaseMajor = Column(String(255), comment='病种专业')
    topPrice = Column(Float(11))
    include = Column(Text)
    exclude = Column(Text)
    count = Column(INTEGER(11), server_default='0', comment='入组病历数量')
    status = Column(INTEGER(1), nullable=False, server_default='2', comment='状态 1停用 2启用 3删除')
    includeText = Column(String(255))
    excludeText = Column(String(255))


class FeeProject(Base):
    __tablename__ = 'feeProject'

    id = Column(INTEGER(11), primary_key=True)
    inpNo = Column(String(255), comment='住院号')
    department = Column(String(255), comment='科室')
    name = Column(String(255), comment='姓名')
    sex = Column(String(255), comment='性别')
    age = Column(String(255), comment='年龄')
    dischargeTime = Column(DateTime, comment='出院时间')
    inpDays = Column(String(255), comment='住院天数')
    diseaseName = Column(String(255), comment='病种')
    mainTreatment = Column(String(255), comment='主要治疗方式')
    costsTotal = Column(String(255), comment='住院费用')
    costsService = Column(String(255), comment='医疗服务类')
    costsMedica = Column(String(255), comment='药品类')
    costsDiagnosis = Column(String(255), comment='诊断类')
    costsConsume = Column(String(255), comment='耗材类')
    costsTreatment = Column(String(255), comment='治疗类')
    costsBlood = Column(String(255), comment='血液和血液制品类')
    costsRecovery = Column(String(255), comment='康复类')
    costsOther = Column(String(255), comment='其他类')
    diseasePay = Column(String(255), comment='单病种结算')
    otherPay = Column(String(255), comment='其他')
    limit = Column(String(255), comment='病种限价')
    status = Column(INTEGER(11), server_default='3', comment='状态 1已取消 2待提交 3待审核 4审核通过 5审核驳回')
    reason = Column(String(255), comment='驳回原因')
    doctorId = Column(String(255))
    doctorName = Column(String(255))
    admitTime = Column(DateTime, comment='入院时间')
    isLeave = Column(String(255))


class FeeApplyForm(Base):
    __tablename__ = 'fee_apply_form'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), comment='病历号')
    patientId = Column(String(255), comment='患者Id')
    single_disease_id = Column(INTEGER(11), comment='费控单病种Id')
    status = Column(INTEGER(11), server_default='3', comment='状态 1已取消 2待提交 3待审核 4审核通过 5审核驳回')
    settlement = Column(INTEGER(11), comment='结算情况,1:单病种结算，2：非单病种结算')
    reason = Column(String(255), comment='驳回原因')
    comment = Column(String(255), comment='其他信息')
    create_time = Column(DateTime, comment='创建时间')
    update_time = Column(DateTime, comment='更新时间')


class FeeDiseaseMajor(Base):
    __tablename__ = 'fee_disease_major'

    id = Column(INTEGER(11), primary_key=True)
    disease_major = Column(String(255), comment='病种分类')
    status = Column(INTEGER(11), server_default='1', comment='状态 0停用 1在用')


class FeeSingleDisease(Base):
    __tablename__ = 'fee_single_disease'

    id = Column(INTEGER(11), primary_key=True)
    disease_name = Column(String(255), comment='病种名称')
    type = Column(String(255), comment='分类')
    main_treatment = Column(String(255), comment='主要治疗方式')
    disease_major = Column(String(255), comment='病种专业')
    top_price = Column(Float(11))
    include = Column(Text)
    exclude = Column(Text)
    include_text = Column(String(255))
    exclude_text = Column(String(255))
    count = Column(INTEGER(11), server_default='0', comment='入组病历数量')
    status = Column(INTEGER(1), nullable=False, server_default='2', comment='状态 1停用 2启用 3删除')
