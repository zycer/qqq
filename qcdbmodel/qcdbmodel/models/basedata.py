# coding: utf-8
"""
基础数据表集合
包括字典表，病历基本信息表，文书，病案首页，医嘱，检验，检查，诊断，手术，体温单
"""

from sqlalchemy import Column, DECIMAL, DateTime, Float, Index, JSON, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT

from sqlalchemylib.sqlalchemylib.connection import Base


class AuditRecord(Base):
    __tablename__ = 'audit_record'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), comment="就诊id")
    group_id = Column(INTEGER(11), server_default='0')
    applyDoctorCode = Column(String(255), comment="申请归档医生编号")
    applyDoctor = Column(String(255), comment="申请归档医生姓名")
    applyTime = Column(DateTime, comment="提交申请时间")
    deptStatus = Column(INTEGER(11), comment="科室质控状态")
    status = Column(INTEGER(11), comment="病案质控状态")
    fpStatus = Column(INTEGER(11), comment="编码质控状态")
    expertStatus = Column(INTEGER(11), comment="专家质控状态")
    timeline = Column(JSON, comment="审核流程")
    message = Column(Text)
    firstProblemCount = Column(INTEGER(11), server_default='0', comment="首页问题数")
    requiredProblemCount = Column(INTEGER(11), server_default='0', comment="首页必填项问题数")
    optionalProblemCount = Column(INTEGER(11), server_default='0', comment="首页非必填项问题数")
    score = Column(Float, server_default=text("'0'"), comment="病案质控节点分数")
    reviewerId = Column(String(255), comment="病案质控节点初审审核人")
    reviewerName = Column(String(255), comment="病案质控节点初审审核人")
    reviewTime = Column(DateTime, comment="病案质控节点初审审核时间")
    problemCount = Column(INTEGER(11), comment="病案质控节点问题数")
    firstpageScore = Column(Float, comment="病案质控节点首页得分")
    finalReviewerName = Column(String(255), comment="病案质控节点终审审核人")
    finalReviewerId = Column(String(255), comment="病案质控节点终审审核人")
    finalReviewTime = Column(DateTime, comment="病案质控节点终审审核时间")
    deptReviewerId = Column(String(255), comment="科室质控节点初审审核人")
    deptReviewerName = Column(String(255), comment="科室质控节点初审审核人")
    deptReviewTime = Column(DateTime, comment="科室质控节点初审审核时间")
    deptScore = Column(Float, comment="科室质控节点得分")
    deptFirstpageScore = Column(Float, comment="科室质控节点首页得分")
    deptProblemCount = Column(INTEGER(11), comment="科室质控节点问题数")
    deptFinalReviewerName = Column(String(255), comment="科室质控节点终审审核人")
    deptFinalReviewerId = Column(String(255), comment="科室质控节点终审审核人")
    deptFinalReviewTime = Column(DateTime, comment="科室质控节点终审审核时间")
    fpReviewerId = Column(String(255), comment="编码质控节点初审审核人")
    fpReviewerName = Column(String(255), comment="编码质控节点初审审核人")
    fpReviewTime = Column(DateTime, comment="编码质控节点初审审核时间")
    fpScore = Column(Float, comment="编码质控节点得分")
    fpFirstpageScore = Column(Float, comment="编码质控节点首页得分")
    fpProblemCount = Column(INTEGER(11), comment="编码质控节点问题数")
    fpFinalReviewerName = Column(String(255), comment="编码质控节点终审审核人")
    fpFinalReviewerId = Column(String(255), comment="编码质控节点终审审核人")
    fpFinalReviewTime = Column(DateTime, comment="编码质控节点终审审核时间")
    expertScore = Column(Float, comment="专家质控节点得分")
    expertReviewerId = Column(String(255), comment="专家质控节点初审审核人")
    expertReviewerName = Column(String(255), comment="专家质控节点初审审核人")
    expertReviewTime = Column(DateTime, comment="专家质控节点初审审核时间")
    expertFirstpageScore = Column(Float, comment="专家质控节点首页得分")
    expertProblemCount = Column(INTEGER(11), comment="专家质控节点问题数")
    expertFinalReviewerName = Column(String(255), comment="专家质控节点终审审核人")
    expertFinalReviewerId = Column(String(255), comment="专家质控节点终审审核人")
    expertFinalReviewTime = Column(DateTime, comment="专家质控节点初审审核时间")
    finalRefuseMessage = Column(String(255), comment='退回重新质控的备注')
    deptFinalRefuseMessage = Column(String(255), comment='科室质控环节退回重新质控的备注')
    fpFinalRefuseMessage = Column(String(255), comment='编码质控环节退回重新质控的备注')
    expertFinalRefuseMessage = Column(String(255), comment='专家质控环节退回重新质控的备注')
    archiveScore = Column(Float, server_default=text("'0'"), comment='院级病案得分，归档病历的最终得分')
    archiveFirstpageScore = Column(Float, server_default=text("'0'"), comment="院级病案首页得分")
    receiveTime = Column(DateTime, comment="签收时间")
    receiveDoctorCode = Column(String(255), comment="签收人")
    archivedType = Column(INTEGER(11), comment="归档类型，1=AI，2=非质控完成归档，3=人工质控审核完成")
    qcCompleteFlag = Column(INTEGER(11), comment="质控完成标记, 1-质控完成")
    operateFlag = Column(INTEGER(11), server_default='0', comment="是否发生过人工质控操作")
    urgeFlag = Column(INTEGER(11), server_default='0', comment="科室质控中已退回的病历是否被催办")

    Index('audit_record_caseId_index', caseId, unique=False)


class Branch(Base):
    __tablename__ = 'branch'
    __table_args__ = {'comment': '医院院区表'}

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255))
    code = Column(String(255))


class Case(Base):
    __tablename__ = 'case'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), comment="就诊id")
    patientId = Column(String(255), comment="患者id")
    name = Column(String(255), comment="患者姓名")
    gender = Column(String(255), comment="患者性别")
    age = Column(INTEGER(11), comment="年龄")
    ageUnit = Column(String(10), comment="年龄单位")
    hospital = Column(String(255), comment="医院")
    branch = Column(String(255), comment="院区")
    admitTime = Column(DateTime, comment="入院时间")
    dischargeTime = Column(DateTime, comment="出院时间")
    attendCode = Column(String(255), comment="责任医生编号")
    attendDoctor = Column(String(255), comment="责任医生姓名")
    status = Column(INTEGER(11), comment="病历状态")
    autoReviewFlag = Column(TINYINT(11), default=1, comment="AI质控标识")
    firstPageFlag = Column(INTEGER(11), server_default='0', comment="缺失首页标识，1:没有病案首页，2：有病案首页")
    departmentId = Column(String(255), comment="入院科室编号")
    department = Column(String(255), comment="入院科室")
    outDeptId = Column(String(255), comment="出院科室编号")
    outDeptName = Column(String(255), comment="出院科室")
    inpDays = Column(INTEGER(11), comment="住院天数")
    visitTimes = Column(INTEGER(11), comment="就诊次数")
    isDead = Column(TINYINT(8), comment="是否死亡")
    diagnosis = Column(String(255), comment="诊断")
    audit_id = Column(INTEGER(11), comment="审核id，对应audit_record.id")
    originCaseId = Column(String(100), comment="运行病历抽取病历对应的原始病历id")
    updateTime = Column(DateTime)
    refuseCount = Column(INTEGER(11), server_default='0', comment="驳回次数")
    tags = Column(JSON, comment="重点病历标签")
    wardId = Column(String(255), comment="出院病区编号")
    wardName = Column(String(255), comment="出院病区名称")
    oper_count = Column(INTEGER(11), server_default='0', comment="手术次数")
    lockoperator = Column(String(100), comment="封存")
    lockreason = Column(String(1024), comment="封存")
    locktime = Column(DateTime, comment="封存")
    tempcol = Column(INTEGER(11))
    ext = Column(JSON)
    hasOutDeptProblem = Column(INTEGER(11), server_default='0', comment="标记是否有出院科室的质控问题")
    feeStatus = Column(INTEGER(11), comment="是否欠费，已废弃")
    isClinical = Column(String(255), comment="临床路径，已废弃")
    patientType = Column(String(255), comment="患者病历类型，1表示门诊，2表示住院，3表示急诊")
    fellowDoctor = Column(String(20), comment="主治医师，该字段没有数据")
    residentDoctor = Column(String(20), comment="住院医师，该字段没有数据")
    bedId = Column(String(255), comment="床号")
    chargeType = Column(String(255), comment='医疗付款方式')
    orgCode = Column(String(255), comment='医疗机构代码，区域病历质控')
    reviewer = Column(String(255), comment="质控人")
    reviewerId = Column(String(255), comment="质控人")
    reviewTime = Column(DateTime, comment="质控时间")
    applyTime = Column(DateTime, comment="申请归档时间")
    applyDoctor = Column(String(255), comment="申请归档医生姓名")
    codeStatus = Column(INTEGER(11), server_default='0', comment='编码状态')
    fix_deadline = Column(DateTime, nullable=False, server_default=text("'2099-12-31 23:59:59'"), comment='驳回整改截止时间')
    inpNo = Column(String(255), comment="住院号")
    datemodified = Column(TIMESTAMP)
    medicalGroupName = Column(String(255), comment="诊疗组名称")
    medicalGroupCode = Column(String(255), comment="诊疗组编号")
    block_time = Column(DateTime, comment="医生端提交首次拦截时间")
    current_total_cost = Column(Float, comment="总费用")
    active_record_id = Column(INTEGER, comment="事中质控id")
    receiveFlag = Column(INTEGER, comment="病案室签收标记,华油独有")

    Index('case_caseId_uindex', caseId, unique=True)
    Index('case_dischargeTime_index', dischargeTime, unique=False)
    Index('case_patientId_visitTimes_index', patientId, visitTimes, unique=False)


class CaseFee(Base):
    __tablename__ = 'case_fee'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), comment='病历号')
    total_cost = Column(Float(asdecimal=True), comment='总费用')
    pub_cost = Column(Float(asdecimal=True), comment='当前累计医保支付费用')
    self_cost = Column(Float(asdecimal=True), server_default='3', comment='累计自付费用')
    items = Column(JSON, comment='费用明细，包含fee_type(费用类型如西药费，手术费),cost（费用金额）')
    comment = Column(String(255), comment='备注')

    Index('case_fee_caseId_index', caseId, unique=False)


class Departmentdict(Base):
    """v4版本的科室字典表"""
    __tablename__ = 'departmentdict'

    id = Column(String(255), primary_key=True)
    code = Column(String(64))
    name = Column(String(255))
    branch = Column(String(255))


class Dept(Base):
    """邵逸夫版本的科室字典表"""
    __tablename__ = 'depts'

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(64))
    name = Column(String(255))
    branch = Column(String(255))
    stay = Column(TINYINT(4))
    status = Column(String(255), comment='用来区分科室和病区')


class Doctor(Base):
    __tablename__ = 'doctor'

    id = Column(String(64), primary_key=True)
    name = Column(String(255))
    branch = Column(String(255))
    department = Column(String(255))
    domain = Column(String(255))
    role = Column(String(255), comment='AFR标记')
    initials = Column(String(255), comment='姓名拼音首字母')
    useflag = Column(INTEGER(11), server_default='0')
    title = Column(String(255), nullable=False, server_default='', comment='医生职称')


class DrugDict(Base):
    __tablename__ = 'drug_dict'

    id = Column(INTEGER(11), primary_key=True, comment='基本id')
    drugCode = Column(String(255), comment='药品编码，需要能和“获取病历医嘱接口”中的项目编码对应')
    drugName = Column(String(255), comment='商品名')
    commonName = Column(String(255), comment='通用名')
    drugType = Column(String(255), comment='药品类型（西药、中成药、中草药）')
    drugClass = Column(String(255), comment='药品分类（抗生素、神经系统药物等）')
    antilevel = Column(String(255), comment='抗菌药物级别（普通抗菌药物、限制级抗菌药物、特殊级抗菌药物）')
    ddd = Column(String(255), comment='抗菌药物ddd值')
    producer = Column(String(255), comment='生产厂家')
    specs = Column(String(255), comment='药品规格')
    form = Column(String(255), comment='剂型')
    usage = Column(String(255), comment='用法')
    dosage = Column(String(255), comment='单次剂量')
    dosage_unit = Column(String(255), comment='单次剂量单位')


class EmrContent(Base):
    __tablename__ = 'emrContent'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), comment="就诊id")
    docId = Column(String(255), comment="文书id")
    emrId = Column(INTEGER(11), comment="关联emrInfo.id，该字段可以废弃")
    htmlContent = Column(LONGTEXT)
    contents = Column(LONGTEXT)
    updateTime = Column(DateTime)
    md5 = Column(String(255))
    version = Column(INTEGER(11), server_default='0')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("emrContent_caseId_docId_index", caseId, docId, unique=False)


class EmrInfo(Base):
    __tablename__ = 'emrInfo'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    docId = Column(String(255))
    documentName = Column(String(255), comment="文书名称")
    department = Column(String(255), comment="书写人对应的科室")
    author = Column(String(255), comment="书写人")
    createTime = Column(DateTime, comment="文书创建时间")
    updateTime = Column(DateTime, comment="文书最后一次更新时间")
    recordTime = Column(DateTime, comment="文书内容对应的记录时间")
    isSave = Column(INTEGER(11), server_default='0', comment="是否正式保存的标记")
    originType = Column(String(255))
    is_deleted = Column(INTEGER(11), server_default='0')
    updated_at = Column(TIMESTAMP)
    doctors = Column(JSON, comment="文书涉及到的医生信息，该字段可以废弃，邵逸夫用于精确驳回给医生的需求")
    checkFlag = Column(INTEGER(11), server_default='0', comment="文书是否审核的标记")
    emrContentId = Column(BIGINT(20), comment="对应最新文书内容emrContent.id")
    refuseCode = Column(String(255), comment="驳回医生的编号")
    categoryId = Column(INTEGER(11), comment="文书类型id，该字段数据不准确可以废弃")
    categoryName = Column(String(255), comment="文书类型名称，字段数据不准确可以废弃")
    md5 = Column(String(255))
    first_save_time = Column(DateTime, comment="文书第一次保存的时间")
    signTime = Column(DateTime, comment="签字时间")
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index('emrInfo_caseId_docId_index', caseId, docId, unique=False)


class ExamContent(Base):
    """检查报告内容"""
    __tablename__ = 'examContent'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), nullable=False)
    itemname = Column(String(255))
    description = Column(LONGTEXT)
    result = Column(Text)
    reportId = Column(String(255), nullable=False)
    is_deleted = Column(TINYINT(1), server_default='0')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("examContent_caseId_index", caseId, unique=False)
    Index("examContent_reportId_index", reportId, unique=False)


class ExamInfo(Base):
    """检查报告"""
    __tablename__ = 'examInfo'

    id = Column(String(255), primary_key=True)
    caseId = Column(String(255))
    examname = Column(String(255))
    examtype = Column(String(255))
    position = Column(String(255))
    requestTime = Column(DateTime)
    reportTime = Column(DateTime)
    requestDepartment = Column(String(255))
    requestDoctor = Column(String(255))
    reviewDoctor = Column(String(255))
    execDepartment = Column(String(255))
    execDoctor = Column(String(255))
    is_deleted = Column(TINYINT(1), server_default='0')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("examInfo_caseId_index", caseId, unique=False)


class Firstpage(Base):
    __tablename__ = 'firstpage'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(100))  # 病历Id caseId
    pname = Column(String(100))  # 姓名 name
    patientId = Column(String(100))  # 病案号 mrno
    psex = Column(String(100))  # 性别 gender
    pbirthday = Column(DateTime)  # 出⽣⽇期 birthday
    citizenship = Column(String(100))  # 国籍 citizenship
    chargetype = Column(String(100))  # 医疗付费⽅式 charge_type
    visitTimes = Column(String(100))  # 住院次数 visittimes
    age = Column(INTEGER(11))  # 年龄 age
    babyage_month = Column(INTEGER(11))  # 不⾜⼀周岁新⽣⼉年龄（⽉）babyage_month
    baby_weight = Column(INTEGER(11))  # 新⽣⼉体重（克） baby_weight
    baby_inhosweight = Column(INTEGER(11))  # 新⽣⼉⼊院体重（克） baby_inhosweight
    bornadress_province = Column(String(255))  # 出⽣地（省、区、市）
    bornadress_city = Column(String(255))  # 出⽣地（市）
    bornadress_county = Column(String(255))  # 出⽣地（县）
    hometown_province = Column(String(255))  # 籍贯（省、区、市）
    hometown_city = Column(String(255))  # 籍贯（市）
    nation = Column(String(100))  # ⺠族
    icd = Column(String(100))  # 身份证号 id_code
    occupation = Column(String(100))  # 职业
    marital_status = Column(String(100))  # 婚姻
    nowadress_province = Column(String(255))  # 现住址（省、区、市）
    nowadress_city = Column(String(255))  # 现住址（市）
    nowadress_county = Column(String(255))  # 现地址（县）
    telephone = Column(String(100))  # 电话
    nowadress_postcode = Column(String(255))  # 现地址邮编
    census_province = Column(String(255))  # 户⼝地址（省、区、市）
    census_city = Column(String(255))  # 户⼝地址（市）
    census_county = Column(String(255))  # 户⼝地址（县）
    census_postcode = Column(String(255))  # 户⼝地址邮编
    work_adress = Column(String(255))  # ⼯作单位及地址
    work_phone = Column(String(255))  # /单位电话
    work_postcode = Column(String(255))  # 单位地址邮编
    concatperson = Column(String(255))  # 联系⼈
    concatperson_relation = Column(String(255))  # 联系⼈关系
    concatperson_adress = Column(String(255))  # 联系⼈地址
    concatperson_phone = Column(String(255))  # 联系⼈电话
    inhos_way = Column(String(255))  # ⼊院途径（⻔诊、急诊、其它医疗机构转⼊等）
    admid = Column(DateTime)  # ⼊院时间 inhosdate
    inhosdept = Column(String(255))  # ⼊院科室 inhosdept
    inhosward = Column(String(255))  # ⼊院病房
    transferdept = Column(String(255))  # 转科科别
    discd = Column(DateTime)  # 出院时间 outhosdate
    outhosdept = Column(String(255))  # 出院科室
    outhosward = Column(String(255))  # 出院病房
    inhosday = Column(String(255))  # 住院天数
    pathology_number = Column(String(255))  # 病理号
    drug_allergy = Column(String(255))  # 药物过敏
    autopsy = Column(String(100))  # 是否⼫检
    bloodtype = Column(String(100))  # ⾎型
    rh = Column(String(100))  # RH⾎型
    director_doctor = Column(String(100))  # 科主任
    chief_doctor = Column(String(100))  # 主任（副主任）医师
    attend_doctor = Column(String(100))  # 主治医师
    resident_doctor = Column(String(100))  # 住院医师
    charge_nurse = Column(String(100))  # 责任护⼠
    physician_doctor = Column(String(100))  # 进修医师
    trainee_doctor = Column(String(100))  # 实习医师
    coder = Column(String(100))  # 编码员
    medical_quality = Column(String(100))  # 病案质量
    qc_doctor = Column(String(100))  # 质控医师
    qc_nurse = Column(String(100))  # 质控护⼠
    qc_date = Column(String(100))  # 质控⽇期
    leavehos_type = Column(String(100))  # 离院⽅式
    againinhosplan = Column(String(100))  # 是否有31天内再住院计划
    braininjurybefore_day = Column(INTEGER(11))  # 颅脑损伤⼊院前昏迷（天）
    braininjurybefore_hour = Column(INTEGER(11))  # 颅脑损伤⼊院前昏迷（⼩时）
    braininjurybefore_minute = Column(INTEGER(11))  # 颅脑损伤⼊院前昏迷（分钟）
    braininjuryafter_day = Column(INTEGER(11))  # 颅脑损伤⼊院后昏迷（天）
    braininjuryafter_hour = Column(INTEGER(11))  # 颅脑损伤⼊院后昏迷（⼩时）
    braininjuryafter_minute = Column(INTEGER(11))  # 颅脑损伤⼊院后昏迷（分钟）
    totalcost = Column(DECIMAL(10, 2))  # 住院总费⽤
    ownpaycost = Column(DECIMAL(10, 2))  # ⾃付⾦额
    generalcost_medicalservice = Column(DECIMAL(10, 2))  # ⼀般医疗服务费
    treatcost_medicalservice = Column(DECIMAL(10, 2))  # ⼀般医疗治疗费
    nursecost_medicalservice = Column(DECIMAL(10, 2))  # 护理费
    othercost_medicalservice = Column(DECIMAL(10, 2))  # 其它费⽤（综合医疗服务类）
    blcost_diagnosis = Column(DECIMAL(10, 2))  # 病理诊断费
    labcost_diagnosis = Column(DECIMAL(10, 2))  # 实验室诊断费
    examcost_diagnosis = Column(DECIMAL(10, 2))  # 影像学诊断费
    clinicalcost_diagnosis = Column(DECIMAL(10, 2))  # 临床诊断项⽬费
    noopscost_treat = Column(DECIMAL(10, 2))  # ⾮⼿术治疗项⽬费
    clinicalcost_treat = Column(DECIMAL(10, 2))  # 临床物理治疗费
    opscost_treat = Column(DECIMAL(10, 2))  # ⼿术治疗费
    anesthesiacost_treat = Column(DECIMAL(10, 2))  # 麻醉费
    surgicacost_trear = Column(DECIMAL(10, 2))  # ⼿术费
    kfcost = Column(DECIMAL(10, 2))  # 康复费
    cmtreatcost = Column(DECIMAL(10, 2))  # 中医治疗费
    wmmedicine = Column(DECIMAL(10, 2))  # ⻄药费
    antibacterial = Column(DECIMAL(10, 2))  # 抗菌药物费
    medicine_cpm = Column(DECIMAL(10, 2))  # 中成药费
    medicine_chm = Column(DECIMAL(10, 2))  # 中草药费
    bloodcost = Column(DECIMAL(10, 2))  # ⾎费
    productcost_bdb = Column(DECIMAL(10, 2), comment="⽩蛋⽩类制品费")
    productcost_qdb = Column(DECIMAL(10, 2), comment="球蛋⽩类制品费")
    productcost_nxyz = Column(DECIMAL(10, 2), comment="凝⾎因⼦类制品费")
    productcost_xbyz = Column(DECIMAL(10, 2), comment="细胞因⼦类制品费")
    consumables_exam = Column(DECIMAL(10, 2), comment="检查⽤⼀次性医⽤材料费")
    consumables_treat = Column(DECIMAL(10, 2), comment="治疗⽤⼀次性医⽤材料费")
    consumables_ops = Column(DECIMAL(10, 2), comment="⼿术⽤⼀次性医⽤材料费")
    othercost = Column(DECIMAL(10, 2), comment="其它费⽤")
    pathology_diag = Column(String(255))
    pathology_code = Column(String(255))
    poison_diag = Column(String(255))
    poison_code = Column(String(255))
    prognosis = Column(String(255))
    consistency_clinic_out = Column(String(100), comment="诊断符合情况标识：门诊与出院")
    consistency_in_out = Column(String(100), comment="诊断符合情况标识：入院与出院")
    consistency_oper_ba = Column(String(100), comment="诊断符合情况标识：术前与术后")
    consistency_clinic_patho = Column(String(100), comment="诊断符合情况标识：临床与病理")
    consistency_radio_patho = Column(String(100), comment="诊断符合情况标识：放射与病理")
    ext_contents = Column(Text, comment='json格式的扩展内容包含了html会用到的所有额外字段')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("firstpage_caseId_index", caseId, unique=False)


class FpDiagnosis(Base):
    """首页诊断列表"""
    __tablename__ = 'fpdiagnosis'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), nullable=False)
    icdcode = Column(String(255))
    icdname = Column(String(255))
    typecode = Column(String(255))
    typename = Column(String(255))
    incondition = Column(String(255))
    prognosis = Column(String(255))
    diagtime = Column(DateTime)
    diagnumber = Column(String(255))
    diagdoctor = Column(String(255))
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    std_code = Column(String(255))
    std_name = Column(String(255))

    Index("fpdiagnosis_caseId_index", caseId, unique=False)


class FpOperation(Base):
    """首页手术操作列表"""
    __tablename__ = 'fpoperation'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    patientId = Column(String(255))
    oper_class = Column(String(255))
    oper_no = Column(String(255))
    oper_code = Column(String(255))
    oper_name = Column(String(255))
    oper_date = Column(String(255))
    oper_level = Column(String(255))
    oper_doctor = Column(String(255))
    assistant_1 = Column(String(255))
    assistant_2 = Column(String(255))
    cut_level = Column(String(255))
    ane_method = Column(String(255))
    ans_doctor = Column(String(255))
    heal_level = Column(String(255))
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    std_code = Column(String(255))
    std_name = Column(String(255))

    Index("fpoperation_caseId_index", caseId, unique=False)


class LabContent(Base):
    __tablename__ = 'labContent'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), nullable=False)
    itemname = Column(String(255))
    code = Column(String(255))
    result = Column(Text)
    unit = Column(String(64))
    abnormalFlag = Column(TINYINT(8))
    valrange = Column(Text)
    reportId = Column(String(255), nullable=False)
    is_deleted = Column(TINYINT(1), server_default='0')
    contents = Column(LONGTEXT)
    resultFlag = Column(String(255))
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    std_code = Column(String(255))
    std_name = Column(String(255))

    Index("labContent_caseId_index", caseId, unique=False)


class LabInfo(Base):
    __tablename__ = 'labInfo'

    id = Column(String(255), primary_key=True)
    caseId = Column(String(255))
    testname = Column(String(255))
    labtype = Column(String(255))
    specimen = Column(String(255))
    requestTime = Column(DateTime)
    reportTime = Column(DateTime)
    requestDepartment = Column(String(255))
    requestDoctor = Column(String(255))
    reviewDoctor = Column(String(255))
    execDepartment = Column(String(255))
    execDoctor = Column(String(255))
    is_deleted = Column(TINYINT(1), server_default='0')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("labInfo_caseId_index", caseId, unique=False)


class MedicalAdvice(Base):
    __tablename__ = 'medicalAdvice'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    patientId = Column(String(255))
    order_no = Column(String(255))
    order_type = Column(String(255))
    set_no = Column(String(255))
    order_seq = Column(String(255))
    date_start = Column(TIMESTAMP)
    date_stop = Column(TIMESTAMP)
    code = Column(String(255))
    name = Column(String(255))
    model = Column(String(255))
    dosage = Column(String(255))
    unit = Column(String(255))
    instruct_code = Column(String(255))
    instruct_name = Column(String(255))
    frequency_code = Column(String(255))
    frequency_name = Column(String(255))
    at_time = Column(String(255))
    doctor_code = Column(String(255))
    doctor = Column(String(255))
    create_at = Column(TIMESTAMP)
    stop_doctor_code = Column(String(255))
    stop_doctor = Column(String(255))
    do_date = Column(String(255))
    nurse = Column(String(255))
    dept_code = Column(String(255))
    dept_name = Column(String(255))
    status = Column(String(255))
    order_flag = Column(String(255))
    order_flag_name = Column(String(255))
    self_flag = Column(String(255))
    print_flag = Column(String(255))
    remark = Column(String(255))
    dept_id = Column(String(255))
    total_dosage = Column(String(255))
    npl = Column(String(255))
    dosage_day = Column(String(255))
    category = Column(INTEGER(11))
    exec_flag = Column(INTEGER(11), server_default='0')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    std_code = Column(String(255))
    std_name = Column(String(255))

    Index("medicalAdvice_caseId_index", caseId, unique=False)


class MzCase(Base):
    __tablename__ = 'mz_case'

    caseId = Column(String(255), primary_key=True, comment='患者就诊唯一编号<必填>')
    patientId = Column(String(255), comment='患者唯一编号<必填>')
    visitId = Column(String(255), comment='患者就诊唯一编号<必填>')
    visitType = Column(String(255), comment='就诊类型01门诊 02住院')
    hospitalName = Column(String(255), comment='医院名称<必填>')
    patientName = Column(String(255), comment='患者姓名<必填>')
    deptId = Column(String(255), comment='就诊科室唯一ID<必填>')
    deptName = Column(String(255), comment='就诊科室名称<必填>')
    doctorId = Column(String(255), comment='医生编号<必填>')
    doctorName = Column(String(255), comment='医生姓名<必填>')
    visitTime = Column(DateTime, comment='就诊时间(格式:yyyy-MM-dd HH:mm:ss)<必填>')
    gender = Column(String(255), comment='性别代码 GB/T2261.1-2003<必填>')
    idType = Column(String(255), comment='证件类型')
    idCard = Column(String(255), comment='证件证号')
    medicalCard = Column(String(255), comment='就诊卡号')
    pregnancy = Column(String(255), comment='妊娠状况 (1: 怀孕 0:未怀孕)')
    pregnancyPeriod = Column(String(255), comment='孕周 单位周')
    menstrualCycle = Column(String(255), comment='是否生理期 1是 0 否')
    birthday = Column(DateTime, comment='出生日期(格式: yyyy-MM-dd)<必填>')
    temperature = Column(String(255), comment='体温(单位：摄氏度)(例如:37.5)')
    weight = Column(String(255), comment='体重(单位：千克)')
    height = Column(String(255), comment='身高(单位：厘米)')
    heartRate = Column(String(255), comment='心率')
    dbp = Column(String(255), comment='舒张压')
    sbp = Column(String(255), comment='收缩压')
    subject = Column(String(255), comment='主诉<必填>')
    presentHistory = Column(String(255), comment='现病史<必填>')
    diseasesHistory = Column(String(255), comment='既往史')
    personHistory = Column(String(255), comment='个人史')
    allergyHistory = Column(String(255), comment='过敏史')
    familyHistory = Column(String(255), comment='家族史')
    marriageHistory = Column(String(255), comment='婚育史')
    menstruationHistory = Column(String(255), comment='月经史')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("mz_case_caseId_index", caseId, unique=False)


class MzDiagnosis(Base):
    """诊断表, 实际上包含门诊和住院的所有诊断.
    这里的诊断与fp_diagnosis不同, fp_diagnosis的来源是病案首页, 这里的是his或emr中的诊断
    """
    __tablename__ = 'mz_diagnosis'

    id = Column(INTEGER(11), primary_key=True, comment='基本id')
    caseId = Column(String(255), comment='门诊就诊id')
    diagId = Column(String(255), comment='门诊诊断id')
    code = Column(String(255), comment='诊断编码，建议使用icd10')
    name = Column(String(255), comment='诊断名称')
    type = Column(String(255), comment='诊断类型，门诊诊断、入院诊断、出院诊断、病理诊断等')
    mainFlag = Column(TINYINT(1), comment='0：次要诊断， 1：主要诊断')
    diagtime = Column(DateTime, comment='诊断时间')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("mz_diagnosis_caseId_index", caseId, unique=False)


class NonDrugOrderDict(Base):
    """非药品收费字典"""
    __tablename__ = 'non_drug_order_dict'

    id = Column(INTEGER(11), primary_key=True, comment='基本id')
    code = Column(String(255), comment='项目编码，需要能和“获取病历医嘱接口”中的项目编码对应')
    itemName = Column(String(255), comment='项目名称')
    producer = Column(String(255), comment='生产厂家')
    unit = Column(String(255), comment='单位')


class NormalDict(Base):
    """
    字典类型包括：
        * order: 医嘱， 包含药品、手术、化验套餐、检查套餐、其他医嘱。 都算这一类
        * fp_operation: 病案手术
        * fp_diagnosis: 病案手术
        * labitem: 检验指标。 检验指标的原始名称使用 样本名称-指标名称  拼接得到
    """
    __tablename__ = 'normal_dict'

    original_code = Column(String(255), primary_key=True, nullable=False)
    original_name = Column(String(255))
    std_code = Column(String(255))
    std_name = Column(String(255))
    item_type = Column(String(255), primary_key=True, nullable=False)


class Operation(Base):
    __tablename__ = 'operation'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    patientId = Column(String(255), comment='病案号 mrno')
    oper_code = Column(String(255), comment='⼿术（操作）编码 opscode')
    oper_name = Column(String(255), comment='⼿术（操作）名称 opsname')
    oper_date = Column(String(255), comment='⼿术（操作）⽇期 opsdate')
    oper_level = Column(String(255), comment='⼿术级别 opslevel')
    oper_doctor = Column(String(255), comment='术者 opsdoctor')
    assistant_1 = Column(String(255), comment='I助 assistantI')
    assistant_2 = Column(String(255), comment='II助 assistantII')
    cut_level = Column(String(255), comment='切⼝愈合等级 cutlevel')
    heal_level = Column(String(255), comment='切⼝愈合等级 cutlevel')
    ane_method = Column(String(255), comment='麻醉⽅式 anesthesiaway')
    ans_doctor = Column(String(255), comment='麻醉医生')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    Index("operation_caseId_index", caseId, unique=False)


class Patient(Base):
    __tablename__ = 'patient'

    id = Column(INTEGER(11), primary_key=True)
    mrn = Column(String(255))
    series = Column(INTEGER(11), nullable=False)
    marriage = Column(String(255), comment='婚姻状况')
    nation = Column(String(255), comment='民族')
    citizenship = Column(String(255), comment='国籍')
    education = Column(String(255), comment='教育程度')
    birthday = Column(String(255), comment='出生日期')
    health_num = Column(String(255), comment='健康卡号')
    birth_addr = Column(String(255), comment='出生地')
    native_addr = Column(String(255), comment='籍贯')
    now_addr = Column(String(255), comment='现住址')
    phone = Column(String(255), comment='联系电话')
    register_addr = Column(String(255), comment='户口地址')
    id_number = Column(String(255), comment='身份证号')
    job = Column(String(255), comment='职业')

    Index("patient_mrn_index", mrn, unique=False)


class RawData(Base):
    """除内置表以外的所有表数据，成都六院=病理表
        * table: 对应etl_config.name
        * key: 基于etl_config中配置的key字段拼接出来的主键
        * caseId: 对应的caseId
        * data: longtext类型， 保存抽取到的一行数据的json内容
        * create_at: 抽取时间，采用数据库自动插入时间即可
    """
    __tablename__ = 'raw_data'

    table = Column(String(255), primary_key=True, nullable=False)
    key = Column(String(255), primary_key=True, nullable=False)
    caseId = Column(String(255), primary_key=True, nullable=False)
    data = Column(LONGTEXT)
    create_at = Column(DateTime)
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))


class TemperatureForm(Base):
    __tablename__ = 'temperature_form'

    id = Column(String(255), primary_key=True, comment='体温单流水号')
    caseId = Column(String(255), comment='病历Id')
    item_name = Column(String(255), comment='项目名称，必须包含舒张压、收缩压、体温、脉搏、心率、身高、体重')
    value = Column(String(255), comment='测量结果')
    unit = Column(String(255), comment='结果单位')
    time = Column(DateTime, comment='测量时间')
    nurse = Column(String(255), comment='操作护士')
    datemodified = Column(TIMESTAMP, nullable=False,
                          server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    Index("temperature_form_caseId_index", caseId, unique=False)


class WardDict(Base):
    __tablename__ = 'warddict'

    id = Column(String(255), primary_key=True)
    code = Column(String(64), comment='病区编码')
    name = Column(String(255), comment='病区名称')
    branch = Column(String(255), default='', comment='所属院区')
    stay = Column(TINYINT(4))
    status = Column(String(255), comment='用来区分科室和病区')


class ActiveRecord(Base):
    __tablename__ = 'active_record'

    id = Column(INTEGER, primary_key=True)
    caseId = Column(String(64), comment='病历id')
    problem_num = Column(INTEGER, comment='问题数')
    operator_id = Column(String(64), comment='操作人id')
    operator_name = Column(String(64), comment='操作人姓名')
    problem_ids = Column(JSON, comment='问题id')
    create_time = Column(DateTime, comment='创建时间')
