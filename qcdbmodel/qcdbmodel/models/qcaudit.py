# coding: utf-8
"""
标准版本病历质控项目相关的表结构

"""

from sqlalchemy import Column, Date, DateTime, Float, Index, LargeBinary, String, TIMESTAMP, Text, text, JSON
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, TEXT, TINYINT

from sqlalchemylib.sqlalchemylib.connection import Base


class AuditEmrInfo(Base):
    __tablename__ = 'auditEmrInfo'
    __table_args__ = {
        'comment': '审核记录与文书版本的关系表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    auditId = Column(INTEGER(11))  # 记录的是保存文书时 case 表记录的 audit_id，无效字段
    caseId = Column(String(255))  # 就诊号
    docId = Column(String(255))  # 文书id
    dataId = Column(INTEGER(11))  # 文书内容数据id
    createTime = Column(DateTime)  # 文书保存时间


class Calendar(Base):
    __tablename__ = 'calendar'
    __table_args__ = {
        'comment': '日历维护记录表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    date = Column(Date, index=True)  # 日期
    isWorkday = Column(TINYINT(1))  # 1表示工作日，0表示非工作日
    comment = Column(String(255))  # 备注


class CaseProblem(Base):
    __tablename__ = 'caseProblem'

    id = Column(BIGINT(20), primary_key=True)
    qcItemId = Column(INTEGER(11), comment='质控点id')
    caseId = Column(String(255))
    docId = Column(String(255))
    linkDocId = Column(String(255), server_default='', comment='关联文书id，文书一致性问题的第二文书')
    title = Column(String(255))
    doctor = Column(String(255))
    department = Column(String(255))
    reason = Column(String(1024), comment="错误提示信息")
    comment = Column(String(1024), comment="备注")
    operator_id = Column(String(255))
    operator_name = Column(String(255))
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    from_ai = Column(TINYINT(1), server_default='0', comment="人工质控问题=0，AI质控问题=1，自定义质控点问题=2")
    is_deleted = Column(TINYINT(1), server_default='0')
    deduct_flag = Column(INTEGER(11), server_default='0', comment="是否扣分")
    score = Column(Float(asdecimal=True), comment="单处扣分")
    problem_count = Column(INTEGER(11), server_default='1', comment="问题数量")
    refuseCount = Column(INTEGER(11), comment="问题驳回次数")
    refuseFlag = Column(INTEGER(11), comment="问题是否驳回标记")
    refuseTime = Column(DateTime, comment="驳回时间")
    doctorCode = Column(String(255), comment="驳回医生编号")
    status = Column(INTEGER(11), comment="如果是 0 且质控点为提示质控点=>提示问题，为1则为普通问题")
    notOpen = Column(INTEGER(11), server_default='0', comment="质控点未开启标记")
    audit_id = Column(INTEGER(11))
    auditType = Column(String(20), comment="质控环节")
    refer = Column(String(1024), comment="演示环境用于高亮定位文书内容的字段")
    overdue_flag = Column(INTEGER(11), server_default='0', comment="时限超时标记")  # 电子病历过级要求
    requirement = Column(String(255), comment='质控项目名称')  # 电子病历过级要求
    is_fix = Column(INTEGER(11), nullable=False, server_default='0', comment='是否整改, 默认0-未整改, 1-已整改')
    is_ignore = Column(INTEGER(11), nullable=False, server_default='0', comment='是否忽略, 默认0-未忽略, 1-乙忽略')
    orgCode = Column(String(64), comment="区域病历质控 机构编号")
    visitType = Column(INTEGER(11), server_default='0', comment="区域病历质控 就诊类型")
    is_valid = Column(INTEGER(11), server_default='1', comment="区域病历质控 问题是否有效标记")

    is_pass = Column(INTEGER(11), server_default='0')  # 废弃字段
    is_expert = Column(TINYINT(1), server_default='0')  # 废弃字段
    taskId = Column(INTEGER(11))  # 废弃字段
    remark = Column(String(255))  # 废弃字段
    remark_doctor = Column(String(64))  # 废弃字段
    remark_doctor_name = Column(String(64))  # 废弃字段
    departmentId = Column(String(255))  # unknown
    doc_data_id = Column(INTEGER(11), server_default='0')  # 用于记录质控问题报警时对应的文书内容id，已废弃
    approve_flag = Column(INTEGER(11), server_default='0')  # 废弃字段，表示是否确认已经修改
    appeal_doctor = Column(String(255))  # 废弃字段
    appeal = Column(String(255))  # 废弃字段
    appeal_time = Column(DateTime)  # 废弃字段
    detail = Column(Text, comment='问题详细说明')  # unknown
    fix_doctor_code = Column(String(255), comment='整改医生code')
    fix_doctor = Column(String(32), comment='整改医生姓名')
    fix_time = Column(DateTime, comment='整改时间')
    active_save_flag = Column(INTEGER, comment='事中质控保存标记, 0-未保存, 1-保存过')

    Index("caseProblem_caseId_docId_index", caseId, docId, unique=False)
    Index("caseProblem_audit_id_index", audit_id, unique=False)
    Index("caseProblem_qcItemId_index", qcItemId, unique=False)


class CheckHistory(Base):
    __tablename__ = 'checkHistory'
    __table_args__ = {
        'comment': '质控日志',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    operatorId = Column(String(255), comment="质控人")
    operatorName = Column(String(255), comment="质控人")
    created_at = Column(DateTime, comment="操作时间")
    action = Column(String(255), comment="操作，比如 添加，删除，驳回，归档")
    content = Column(String(255), comment="操作内容")
    comment = Column(String(255), comment="备注")
    type = Column(String(255), comment="病历类型或者文书类型")
    expert = Column(INTEGER(11), server_default='0')
    auditType = Column(String(20), comment="质控环节")
    auditStep = Column(String(20))  # 表示初审还是终审，无效字段，同一质控环节不需要区分

    Index("checkHistory_caseId_index", caseId, unique=False)


class Department(Base):
    __tablename__ = 'department'

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255), comment="科室编号")
    name = Column(String(255), comment="科室名称")
    branch = Column(String(255), comment="院区")
    deptType = Column(INTEGER(11), nullable=False, server_default='0', comment='内外科类型1-内科, 2-外科')
    sort_no = Column(INTEGER(11), server_default='1', comment='名称排序字段')
    std_code = Column(String(255), comment='标准编码')
    std_name = Column(String(255), comment='标准名称')


class Ward(Base):
    __tablename__ = 'ward'

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(64), comment="病区编号")
    name = Column(String(255), comment="病区名称")
    branch = Column(String(255), comment="院区")
    stay = Column(TINYINT(4))  # 邵逸夫医院接口中用来表示科室类别，无效字段，废弃字段
    status = Column(String(255), comment='用来区分科室和病区')  # 无效字段
    sort_no = Column(INTEGER(11), server_default='1', comment='名称排序字段')


class Diagnosis(Base):
    """诊断字典表，已废弃
    """
    __tablename__ = 'diagnosis'

    id = Column(INTEGER(11), primary_key=True)
    icd10 = Column(String(255))
    name = Column(String(255))


class DiagnosisDict(Base):
    __tablename__ = 'diagnosis_dict'

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255), comment="诊断编码")
    name = Column(String(255), comment="诊断名称")
    initials = Column(String(255), comment="拼音首字母")


class Document(Base):
    __tablename__ = 'documents'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255), comment="文书名称")
    standard_name = Column(String(255), comment="标准文书")  # 标准文书名称对照
    type_name = Column(String(255), comment="文书目录名称")  # 文书目录名称
    type_order = Column(INTEGER(11), server_default='0', comment="文书目录排序顺序")  # 按照文书目录排序顺序
    index = Column(INTEGER(11), server_default='100', comment="文书排序顺序")  # 按照文书排序顺序
    type = Column(String(255))  # 第一版文书目录类型，无效字段，废弃字段
    standard_emr_id = Column(INTEGER(11))  # 无效字段 废弃字段
    comment = Column(String(64))


class DocumentClassifyRegexp(Base):
    """文书名称标准话对照正则匹配规则
    """
    __tablename__ = 'document_classify_regexp'

    id = Column(INTEGER(11), primary_key=True)
    regexp = Column(String(1024), comment="正则表达式")
    standard_name = Column(String(255), comment="标准文书名称")  # 标准文书名称对照


class Drugclass(Base):
    __tablename__ = 'drugclasses'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255))
    category = Column(String(255))


class ExpertUser(Base):
    __tablename__ = 'expert_user'
    __table_args__ = {
        'comment': '抽取病历质控专家',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    auditType = Column(String(100), nullable=False)
    userId = Column(String(100), nullable=False)
    userName = Column(String(100), nullable=False)
    caseType = Column(String(255))
    id = Column(INTEGER(11), primary_key=True)


class MedicalAdviceType(Base):
    __tablename__ = 'medicalAdviceType'
    __table_args__ = {
        'comment': '医嘱类型字典',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    type = Column(String(255))
    name = Column(String(255))


class OperationDict(Base):
    """病历列表页 - 手术字典"""
    __tablename__ = 'operation_dict'

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255))
    name = Column(String(255))
    initials = Column(String(255))


class RefuseDetail(Base):
    __tablename__ = 'refuse_detail'
    __table_args__ = {
        'comment': '驳回记录详情',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    audit_id = Column(INTEGER(11))
    history_id = Column(INTEGER(11), server_default='0', comment="驳回记录id")
    created_at = Column(DateTime, comment="创建时间")
    is_deleted = Column(INTEGER(11))
    reviewer = Column(String(255), comment="质控人员")
    doctor = Column(String(255), comment="驳回医生编号")
    apply_flag = Column(INTEGER(11), comment="是否重新申请标记")
    apply_time = Column(DateTime, comment="重新申请时间")

    Index("refuse_detail_doctor_index", doctor, unique=False)
    Index("refuse_detail_history_id_index", history_id, unique=False)


class RefuseHistory(Base):
    __tablename__ = 'refuse_history'
    __table_args__ = {
        'comment': '驳回记录整改书',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(BIGINT(20), primary_key=True)
    caseId = Column(String(255))
    patient_id = Column(String(64), comment="患者id")
    visit_times = Column(INTEGER(11), server_default='0', comment="就诊次数")
    audit_id = Column(INTEGER(11), server_default='0')
    auditType = Column(String(255), server_default='0', comment="质控环节")
    qc_doctor = Column(String(255), comment="质控人")
    refuse_time = Column(DateTime, comment="驳回时间")
    type = Column(String(255), server_default='0', comment='退回类型, 默认0-退回, 1-追加退回')
    problems = Column(Text, comment="驳回问题详细信息")
    lost_score = Column(String(64), comment="扣分")
    problemCount = Column(INTEGER(11), server_default='0', comment="问题数")
    comment = Column(String(64), comment="备注")
    fix_deadline = Column(DateTime, comment='整改期限')
    revoke_flag = Column(INTEGER(11), server_default='0', comment="是否撤销驳回的标记")
    revoke_time = Column(DateTime, comment="撤销驳回的时间")
    revoke_doctor = Column(String(255), comment="撤销驳回的医生")
    level = Column(INTEGER(11), server_default='0', comment="三级质控驳回环节等级")  # 邵逸夫医院版本=3 病案质控
    emr_message = Column(Text, comment="emr驳回接口返回值")  # 邵逸夫医院版本 记录emr接口返回的驳回操作创建的记录id列表

    qc_type = Column(String(64))  # 驳回类型，科室，病案，专家 废弃字段
    refuse_no = Column(INTEGER(11), server_default='0')  # 驳回序号，第几次驳回 废弃字段
    from_id = Column(String(64))  # 驳回操作人 废弃
    from_name = Column(String(64))  # 驳回操作人 废弃
    from_dept = Column(String(64))  # 驳回操作科室 废弃
    to_id = Column(String(64))  # 驳回给谁 废弃
    to_name = Column(String(64))  # 驳回给谁 废弃
    to_dept = Column(String(64))  # 驳回给谁科室 废弃
    report = Column(Text)  # 整改书 废弃
    lostScore = Column(Float, server_default=text("'0'"))

    Index("refuse_history_audit_id_index", audit_id, unique=False)


class SampleRecord(Base):
    __tablename__ = 'sample_record'

    id = Column(INTEGER(11), primary_key=True)
    createdAt = Column(DateTime, nullable=False)
    operatorId = Column(String(100))
    operatorName = Column(String(100))
    isAssigned = Column(TINYINT(1))
    auditType = Column(String(100), nullable=False)
    caseType = Column(String(100))
    sampledCount = Column(INTEGER(11), server_default='0', comment="已抽取病历数")
    sampleBy = Column(String(255), comment="抽取依据")
    lastOperation = Column(INTEGER(11), comment="最后一次操作记录id")
    submit_flag = Column(INTEGER(11), server_default='0', comment="提交标记")


class SampleRecordItem(Base):
    __tablename__ = 'sample_record_item'

    recordId = Column(INTEGER(11), nullable=False)
    id = Column(INTEGER(11), primary_key=True)
    expertId = Column(String(100))
    caseId = Column(String(100), nullable=False)
    expertName = Column(String(100))
    auditType = Column(String(100), nullable=False)
    isMannalAssigned = Column(TINYINT(4), server_default='0')
    is_read = Column(INTEGER(11), nullable=False, server_default='0', comment='医生端抽检病历是否已读, 0-未读, 1-已读')
    originCaseId = Column(String(255), comment='原始caseId')

    Index("sample_record_item_UN", recordId, caseId, unique=True)
    Index("sample_record_item_caseId_auditType_index", caseId, auditType, unique=False)


class ScoreReportQcitem(Base):
    __tablename__ = 'score_report_qcitems'
    __table_args__ = {
        'comment': '质控评分报告和质控点关系对照表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255), comment="质控评分表编号")
    name = Column(String(255), comment="质控评分表模板占位符")
    qcitems = Column(String(1024), comment="质控点列表，用逗号分隔")
    message = Column(String(255), comment="备注")


class ScoreReportTemplate(Base):
    __tablename__ = 'score_report_template'
    __table_args__ = {
        'comment': '质控评分表模板',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    code = Column(String(255), primary_key=True, comment="质控评分表编号")
    template = Column(TEXT, comment="模板html，包含占位符格式{patientId}")


class Tag(Base):
    __tablename__ = 'tags'
    __table_args__ = {
        'comment': '重点病历标签',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(100), nullable=False, comment="标签名称")
    code = Column(String(100), nullable=False, comment="标签编号")  # 需要和case表tags字段中保持一致
    status = Column(INTEGER(11), server_default='1', comment="状态，1：默认选中，2：取消默认选中")
    orderNo = Column(INTEGER(11), server_default='1', comment="排序")
    icon = Column(LargeBinary)
    is_deleted = Column(INTEGER(11), server_default='0')


class TagsQc(Base):
    __tablename__ = 'tags_qc'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(100))
    code = Column(String(255))
    status = Column(TINYINT(4))
    no = Column(INTEGER(11))


class WardDoctor(Base):
    __tablename__ = 'ward_doctor'
    __table_args__ = {
        'comment': '病区分配时用户指定的病区分配医生',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    ward = Column(String(128), comment='病区名称')
    doctorName = Column(String(128), comment='病区指定的分配医生姓名')
    user_id = Column(String(128), comment='保存用户')
    create_time = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    doctorId = Column(String(128), comment='病区指定的分配医生ID')


class OrganDict(Base):
    """区域病历质控 - 机构字典"""
    __tablename__ = 'organ_dict'

    code = Column(String(64), primary_key=True, unique=True)
    name = Column(String(255))


class ExternalLink(Base):
    """其它系统外链"""
    __tablename__ = 'external_link'

    id = Column(INTEGER(11), primary_key=True)
    system = Column(String(255), comment="系统名")
    title = Column(String(255), comment="外链名称")
    url = Column(String(255), comment="外链地址")
    icon = Column(Text, comment="icon")


class SampleOperation(Base):
    """病历抽取操作日志"""
    __tablename__ = "sample_operation"

    id = Column(INTEGER(11), primary_key=True)
    sample_id = Column(INTEGER(11), comment="抽取记录id")
    name = Column(String(255), comment="操作名称")
    content = Column(String(255), comment="操作具体描述")
    sample_by = Column(String(255), comment="抽取依据")
    conditions = Column(Text, comment="指定抽取条件")
    sampled_count = Column(INTEGER(11), comment="实际抽取数量")
    sampled_case = Column(Text, comment="抽取到的病历号")
    operator = Column(String(255), comment="操作人")
    operate_time = Column(DateTime, comment="操作时间")
    params = Column(JSON, comment="请求参数")


class SampleFilter(Base):
    """
    抽取条件表
    """
    __tablename__ = "sample_filter"

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(64), comment="名称")
    describe = Column(String(255), comment="描述")
    range = Column(Text, comment="抽取范围, 全部病历、特定")
    is_delete = Column(INTEGER, comment="删除标记, 1-已删除")
    create_time = Column(DateTime, comment="创建时间")
    filter = Column(Text, comment="抽取条件")
    auditType = Column(String(32), comment="质控类型")
    caseType = Column(String(16), comment="病历类型, 终末-final、归档-archive、运行-running等")


class SampleTask(Base):
    """
    抽取定时任务表
    """
    __tablename__ = "sample_task"

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(64), comment="名称")
    type = Column(String(64), comment="任务类型, 抽取、分配")
    days = Column(INTEGER, comment="执行频率, 每隔几天执行一次")
    first_sample_time = Column(DateTime, comment="首次执行时间")
    status = Column(INTEGER, comment="0-不展示,1-启用,2-停用")
    is_delete = Column(INTEGER, comment="1-删除")
    create_time = Column(DateTime, comment="创建时间")
    query_filter = Column(Text, comment="列表查询条件")
    sample_filter = Column(Text, comment="抽取条件")
    assign_doctor = Column(Text, comment="分配医生")
    notCurrentDeptFlag = Column(INTEGER, comment="0-可以分配本科室, 1-否")
    next_run_time = Column(DateTime, comment="下次运行时间")
    auditType = Column(String(16), comment="质控类型")
    caseType = Column(String(16), comment="病历类型, 终末-final、归档-archive、运行-running等")


class CaseProblemRecord(Base):
    """
    病历问题操作记录表
    """
    __tablename__ = "case_problem_record"

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(128), comment="病历id")
    qcItemId = Column(INTEGER(11), comment="质控点id")
    action = Column(String(128), comment="问题操作, 提出问题, 解决问题等")
    create_time = Column(DateTime, comment="操作时间")
    doctor_name = Column(String(128), comment="操作医生姓名")
    doctor_code = Column(String(128), comment="操作医生id")
    auditType = Column(String(128), comment="操作节点")

    Index("case_problem_record_caseId_qcItemId_index", caseId, qcItemId, unique=False)
