#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 18:15:54

'''

# 科室质控
AUDIT_TYPE_DEPARTMENT = 'department'

# 全院级别质控
AUDIT_TYPE_HOSPITAL = 'hospital'

# 首页编码质控
AUDIT_TYPE_FIRSTPAGE = 'firstpage'

# 专家质控
AUDIT_TYPE_EXPERT = 'expert'

# 事中质控
AUDIT_TYPE_ACTIVE = 'active'

# 初审
AUDIT_STEP_AUDIT = 'audit'
# 终审
AUDIT_STEP_RECHECK = 'recheck'

# 病历状态常量已归档
CASE_STATUS_ARCHIVED = 3
# 病历状态常亮已退回给临床
CASE_STATUS_REFUSED = 4
# 病历状态常量待审核
CASE_STATUS_APPLIED = 1
# 未申请
CASE_STATUS_NOTAPPLIED = 5

ALL_AUDIT_TYPE = [
    AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT,
    AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, AUDIT_TYPE_ACTIVE
]

AUDIT_STATUS = [
    {
        "dbid": 1,
        "name": "待质控",
        "filter": [1, 7],
        "returnid": 1,
    }, {
        "dbid": 3,
        "name": "已质控",
        "filter": [3, 6],
        "returnid": 3
    }, {
        "dbid": 4,
        "name": "已退回",
        "filter": [4],
        "returnid": 4
    }, {
        "dbid": 7,
        "name": "待质控",
        "hideflag": 1,
        "returnid": 1
    }, {
        "dbid": 5,
        "name": "未申请",
        "hideflag": 1
    }, {
        "dbid": 6,
        "name": "已审核",
        "hideflag": 1
    }
]
RECHECK_STATUS = [
    {
        "dbid": 3,
        "returnid": 1,
        "name": "待审核",
        "filter": [3],
    }, {
        "dbid": 4,
        "returnid": 4,
        "name": "已退回返修",
        "filter": [4],
    }, {
        "dbid": 6,
        "returnid": 3,
        "name": "已审核",
        "filter": [6],
    }, {
        "dbid": 7,
        "returnid": 7,
        "name": "退回重新质控",
        "filter": [7],
    }
]

EXPORT_FILE_AUDIT_TYPE = {
    AUDIT_TYPE_DEPARTMENT: "科室",
    AUDIT_TYPE_HOSPITAL: "病案",
    AUDIT_TYPE_FIRSTPAGE: "编码",
    AUDIT_TYPE_EXPERT: "专家",
    AUDIT_TYPE_ACTIVE: "事中",
}

EXPORT_FILE_AUDIT_STEP = {
    AUDIT_STEP_AUDIT: "质控",
    AUDIT_STEP_RECHECK: "审核"
}

CASE_LIST_PROBLEM_COUNT = {
    AUDIT_TYPE_DEPARTMENT: "deptProblemCount",
    AUDIT_TYPE_EXPERT: "expertProblemCount",
    AUDIT_TYPE_FIRSTPAGE: "fpProblemCount",
    AUDIT_TYPE_HOSPITAL: 'problemCount',
    AUDIT_TYPE_ACTIVE: 'sum_problem_count',
}

CASE_LIST_AUDIT_TIME = {
    AUDIT_TYPE_DEPARTMENT: "deptReviewTime",
    AUDIT_TYPE_EXPERT: "expertReviewTime",
    AUDIT_TYPE_FIRSTPAGE: "fpReviewTime",
    AUDIT_TYPE_HOSPITAL: 'reviewTime',
    AUDIT_TYPE_ACTIVE: 'create_time',
}

CASE_LIST_CASE_SCORE = {
    AUDIT_TYPE_DEPARTMENT: "deptScore",
    AUDIT_TYPE_EXPERT: "expertScore",
    AUDIT_TYPE_FIRSTPAGE: "fpScore",
    AUDIT_TYPE_HOSPITAL: 'score',
    AUDIT_TYPE_ACTIVE: 'ifnull(sum_score, 100)',
}

CASE_LIST_AUDIT_DOCTOR = {
    AUDIT_TYPE_DEPARTMENT: "deptReviewerName",
    AUDIT_TYPE_EXPERT: "expertReviewerName",
    AUDIT_TYPE_FIRSTPAGE: "fpReviewerName",
    AUDIT_TYPE_HOSPITAL: 'reviewerName',
    AUDIT_TYPE_ACTIVE: 'operator_name',
}

QCITEM_CATEGORY = {
    1: "时效性",
    2: "一致性",
    3: "完整性",
    4: "正确性"
}

QCITEM_CATEGORY_DICT = {
    "时效性": 1,
    "一致性": 2,
    "完整性": 3,
    "正确性": 4
}

QCITEM_TAGS = {
    'single': '单病种',
    'icderr': '编码',
}

LAB_ABNORMAL_ICON = {
    '超出正常': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAbZJREFUWEftlstKw0AUhs9MS2Pj1pUovoCX5xBxo+CVLty4SqaFPkehTWblRpAqKuhGxOfw8gKiuHJrako7R6ZUiGWSTKaFIiTLcHL+L//5czIEpnyRKetDDvC/HQgZW5YZsjzvxTRLxg4ErnuDiFtSmBBya/v+tgmEEUCHsYoQ4iwqSAEqZc7bWSEyAwSM7YEQbQQoRMUIQB8ADm3Or7JAZAKIE/8VNIHQBkgTN4XQAtAVN4FIBVCJS6tVGYje0x1HIkDgOLsAcK5qjACXf0JI6f5oOHUgYgECxnZAiIu4t/pyHIwCzHJO4twCSg9sz7tWfR1KAKzX5zph+IoAdtxcVQCyNgYiKFvWEmk0PkchlABhtbra6/cfk0IVBzCAUIyuWCisWa3WkxYAIko77wBxgwAEQOnRqIVJAEMn5AhPBy4Scm973iYh5M/YBms8bmtJiG6ttlIqFj9U1qUByL5ylN1eb77UbD6rxBMB0tapDkBajxwgd2AsBwLXfUPEheGJ6N32/UWd0GntAZ1G346zLgg5kbUU8XiG8wed5yYGYCKm/S+YVHOdPqnnAZ0m49TkAFN34Ae4WuMhC4fvPQAAAABJRU5ErkJggg==',
    '低于正常': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAdJJREFUWEftlE9LAlEUxe91nMCg2uSiwkxtEdSmaNUuV6JO275FxWiQtXFTFuqAfou2adKqZZugWiS0SK2kgmxTQS7882IUZdIZ5/mIpHCWj3vv+b1zzxuEHn/YY33oA/xtB7buk3Y5Q/tWb5Y1S8wO+DOJQBXInixsANyOOIQQCwQzgJhJvAGQ4boovksOYeSXAY6IUlByrDBdhqlJFhYzfYD/7kDgOWUuFSuriIbbsM1z0ppwmgxs5o5dhFSneRN3GBpzF9ReiWoIpfyZ6bH0miYEbLVHBhiLOoQN5QA9ADGbiAEha7V+hNwEPzorWpaKrRCqAOJdah4q5YtvxYhxyS6sN846ASjFmzM444I05b6kAgg+JQY/iuSGAFi0ILQA1MQRID9kwpnguPBJBSAX+R+Sc9USOQUgZjUINQAN8RejccB5YHWlqTPQKOwE0dhvcyhivO0MsMAb+WUt8Xq+dD5NCL1GCnEqgI7r0ITQv3mjVdcB3XW0QWDBwKMzMum91jWJZgXKIfrr6E6cegV0EN2LMwHITbUfVbV8DgS4GhxChUNuMWzzXNHYrqyhzkDrYF826QMgO/Vz3I3avdFuxZkdYBHS6mF24Kcg+gB9B74A5cjcIW8Qv4QAAAAASUVORK5CYII=',
    '正常': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAIKADAAQAAAABAAAAIAAAAACshmLzAAAAd0lEQVRYCe3RMQ6AIAwFUNpzeCFHd2cOxczu6IU8ByV/cGsTEnTR34k0pS2PlBgUoAAFKECBvwtIBFDqsbZmxcyWqGYkLyKXquS8b6dXr14SuSeGow8egF44exEu4BW/kQsXABv4ZofeXzDbh/cpQAEKUIAC3xXoOTUcCE6/h8MAAAAASUVORK5CYII=',
}

# 最基本的标准文书名称正则匹配规则
EMR_DOCUMENTS_REG = [
    ('病案首页', '$mr_front_sheet', '(住院病案|病历|病案)[首附]页'),
    ('首次病程记录', '$first_course_record', '^((?!术后).)*首次病程记?录?|首程中.*补充'),
    ('病程记录', '$course_record', '^((?!首次).)*病程录|治疗记录单|查房记录'),
    ('交接班记录', '$course_record$shift_record', '交接?班(记|病程)录'),
    ('转科记录', '$course_record$transferred_record', '转科记录'),
    ('转入记录', '$course_record$transferred_record$transferred_in_record', '转入记录|接科（转运）记录'),
    ('ICU转病房记录', '$course_record$transferred_record$transferred_in_record$transferred_in_record_from_icu', 'ICU转病房记录'),
    ('入ICU记录', '$course_record$transferred_record$transferred_in_record$transferred_in_record_to_icu', '[入人]E?ICU'),
    ('转出记录', '$course_record$transferred_record$transferred_out_record', '转出记录|转科（转运）记录'),
    ('病房转ICU记录', '$course_record$transferred_record$transferred_out_record$transferred_out_record_to_icu', '病房转ICU记录'),
    ('出ICU记录', '$course_record$transferred_record$transferred_out_record$transferred_out_record_from_icu', '出ICU记录'),
    ('转院记录', '$course_record$hospital_transfer_record', '转院记录'),
    ('阶段小结', '$course_record$stage_summary', '阶段小结'),
    ('科室大查房记录', '$course_record$big_check_department', '科室大查房'),
    ('抢救记录', '$course_record$rescue_record', '抢救(记|病程)录'),
    ('会诊记录', '$course_record$consultation_note', '(会诊|MDT|多学科综合诊疗).{0,2}(记|病程)录|会诊$'),
    ('术后首次病程记录', '$course_record$first_course_record_after_operation', '术后首[次程]病程记?录'),
    ('查房记录', '$course_record$check_record', '查房记录'),
    ('术前查房记录', '$course_record$check_record$check_record_before_operation', '术前.*查房|术前记录'),
    ('术后第一天查房记录', '$course_record$check_record$check_record_first_day_after_operation', '术后第[1一]天'),
    ('术后第二天查房记录', '$course_record$check_record$check_record_second_day_after_operation', '术后第[2二]天'),
    ('术后第三天查房记录', '$course_record$check_record$check_record_third_day_after_operation', '术后第[3三]天'),
    ('日常查房记录', '$course_record$check_record$daily_check_record', '日常查房记录'),
    ('危急值处理记录', '$course_record$check_record$daily_check_record$critical_value_handling_record', '危急值(处理|记录)'),
    ('上级医师查房记录', '$course_record$check_record$check_record_superior_physician', '上级医?[生师]?查房记录'),
    ('科主任查房记录', '$course_record$check_record$check_record_superior_physician$check_record_department_director',
     '科主任查房记录'),
    ('主治医师查房记录', '$course_record$check_record$check_record_superior_physician$check_record_attending_physician',
     '(Fellow|主治医)[师|生]查房'),
    ('主（副）任医师查房记录', '$course_record$check_record$check_record_superior_physician$check_record_chief_physician',
     '副?主.*任医师查房记录'),
    ('输血前评估记录', '$course_record$pre_transfusion_evaluation', '输血前评估记录'),
    ('输血后评估记录', '$course_record$evaluation_after_transfusion', '输血后评估记录'),
    ('输血记录', '$course_record$blood_transfusion_record', '血液制品输注病程录|输血记录'),
    ('转组记录', '$course_record$group_transfer_record', '转组(病程|记)录'),
    ('产褥复旧记录（阴道分娩）', '$course_record$puerperal_involution_record', '产褥复旧记录（阴道分娩）'),
    ('新生儿记录', '$course_record$neonatal_records', '新生儿记录'),
    ('谈话记录', '$conversation_note', '谈话'),
    ('入院七十二小时谈话记录', '$conversation_note$conversation_note_within_72h', '(七十二|72)小时谈话记录'),
    ('术前谈话记录', '$conversation_note$conversation_note_before_operation', '术前谈话'),
    ('术后谈话记录', '$conversation_note$conversation_note_after_operation', '术后谈话'),
    ('入ICU谈话记录', '$conversation_note$conversation_note_icu', '入住重症监护室.*谈话记录'),
    ('五日未手术谈话记录', '$conversation_note$conversation_no_operation_within_5d', '五日未手术谈话记录'),
    ('知情同意书', '$informed_consent', '(告知|同意|承诺)书|(病情|特殊|特殊情况)告知|Informed Consent|知情(同意|签署)'),
    ('检查同意书', '$informed_consent$inspection_consent', '检查知情同意书?'),
    ('治疗同意书', '$informed_consent$treatment_consent', '(普萘洛尔|临床试验|治疗|用药).{0,5}知情同意书?'),
    ('镇静治疗同意书', '$informed_consent$treatment_consent$sedation_treatment_consent', '镇静治疗同意书'),
    ('癌痛治疗同意书', '$informed_consent$treatment_consent$cancer_pain_treatment_consent', '癌痛治疗同意书'),
    ('激素治疗同意书', '$informed_consent$treatment_consent$hormone_treatment_consent', '激素治疗同意书'),
    ('抗凝同意书', '$informed_consent$treatment_consent$anticoagulation_consent', '抗凝同意书'),
    ('死亡告知书', '$informed_consent$death_notice', '死亡告知书'),
    ('自动出院告知书', '$informed_consent$auto_discharge_notice', '自动出院告知书'),
    ('静脉血栓形成告知书', '$informed_consent$venous_thrombosis_notice', '静脉血栓形成告知书'),
    ('拒绝或放弃医学检查告知书', '$informed_consent$waiver_examination_consent', '拒绝或放弃医学检查告知书'),
    ('拒绝或放弃医学治疗告知书', '$informed_consent$waiver_treatment_consent', '拒绝或放弃医学治疗告知书'),
    ('输血同意书', '$informed_consent$blood_transfusion_consent', '(输血|血浆注射).{0,8}知情同意书?'),
    ('自费药物同意书', '$informed_consent$self_pay_consent', '自费药物知情同意书'),
    ('病危（重）通知书', '$informed_consent$critical_consent', '病[重危].{0,3}[通告]知'),
    ('病危通知书', '$informed_consent$critical_consent$critical_illness_consent', '病危通知书'),
    ('病重通知书', '$informed_consent$critical_consent$critical_serious_illness_consent', '病重通知书'),
    ('麻醉知情同意书', '$informed_consent$anesthesia_consent', '(麻醉|阻滞术|阻滞治疗术).{0,3}知情同意书?|麻醉科.受试者入组期基本情况'),
    ('操作同意书', '$informed_consent$invasive_operation_consent', '(穿刺|活检|[置插]管|透析|清宫|流产|镜检查|宫内节育器|超声引导注射|引流).*知情同意书'),
    ('手术知情同意书', '$informed_consent$operation_consent',
     '((置换|成形|切除|减灭|分离|移植|固定|扩张|内瘘|治疗|手|矫正)术|(靶向|溶栓|射频|放射)治疗).*(知情)?(同意|自愿)书?'),
    ('麻醉访视记录', '$anesthesia_visit_record', '麻醉访视记录|C.{1,2}D.{1,2}访视记录'),
    ('麻醉术前访视记录', '$anesthesia_visit_record$anesthesia_visit_record_before', '麻醉前访视(单|记录)'),
    ('麻醉术后访视记录', '$anesthesia_visit_record$anesthesia_visit_record_after', '麻醉.*术后随访'),
    ('麻醉记录', '$anesthesia_record', '麻醉记录'),
    ('24小时出入院记录', '$admission_record_within_24h', '24(小时|h)内?(入出|出入)院?记录'),
    ('住院证', '$admission_card', '住院(证|通知单)'),
    ('入院须知', '$admission_notice', '(入院|住院病人)(须知|告知书)$'),
    ('入院记录', '$admission_record', '^((?!24).)*(大病[史历例]|入院记录)'),
    ('再次入院记录', '$admission_record$readmission_record', '再次入院记录'),
    ('出院记录', '$discharge_record', '^((?!24).)*出院.{0,2}(记录|小结)'),
    ('母婴同室新生儿出院记录', '$discharge_record$newborns_discharge_record', '母婴同室新生儿出院.{0,2}(记录|小结)'),
    ('产科出院记录', '$discharge_record$obstetric_discharge_record', '产科出院记录'),
    ('疑难病例讨论', '$difficult_cases_discussion', '疑难病例讨论'),
    ('危重病例讨论', '$serious_cases_discussion', '危重病例讨论'),
    ('超30天病例讨论', '$over_30d_cases_discussion', '超30天病例讨论'),
    ('死亡病例讨论记录', '$death_cases_discussion', '死亡病例讨论记录'),
    ('重大疑难手术审批报告', '$difficult_operation_report', '重大疑难(手术)?审批报告'),
    ('有创操作记录', '$invasive_operation_record',
     '宫内节育器取出术|(CT|超声)引导.*阻滞|(放置|闭式术|松解|引流|穿刺|活检|[置插]管|透析|清宫|流产|镜检查|宫内节育器|超声引导|[置介]入|破膜|房颤消融).*(术|记录|治疗表单)$'),
    ('清宫手术记录', '$invasive_operation_record$records_of_curettage', '清宫'),
    ('手术记录', '$operation_record', '(手术|环切|造瘘|术中)记录|造口手术'),
    ('剖宫产手术记录', '$operation_record$cesarean_section_records', '剖宫产术记录表'),
    ('日间手术记录', '$operation_record$daily_operation_record', '日间手术记录'),
    ('手术风险评估记录', '$surgical_risk_assessment', '手术风险评估记录'),
    ('术前讨论及术前小结', '$preoperative_discussion_summary', '术前讨论及小结'),
    ('术前讨论', '$preoperative_discussion_summary$preoperative_summary', '术前讨论(记录)?$'),
    ('非计划二次手术讨论记录', '$preoperative_discussion_summary$preoperative_summary$unplanned_2nd_preoperative_summary',
     '非计划二次手术讨论记录'),
    ('术前小结', '$preoperative_discussion_summary$preoperative_discussion', '术前小结$'),
    ('手术安全核查记录', '$operation_safety_record', '术前安全核查'),
    ('术前准备核查表', '$preoperative_checklist', '术前准备核查'),
    ('死亡记录', '$death_record', '^((?!24).)*死亡记录'),
    ('24小时入院死亡记录', '$death_record_within_24h', '24小时内?入院死亡记录'),
    ('会诊意见', '$consultation_opinion', '(会诊|MDT|多学科综合诊疗).{0,2}(结果|意见|回复)'),
    ('会诊申请单', '$consultation_application', '(会诊|MDT|多学科综合诊疗)申请'),
    ('院外专家会诊申请单', '$consultation_application$outside_expert_consultation_application', '院外专家会诊申请单'),
    ('知情选择书', '$informed_choice', '(知情选择书|患者授权书)$'),
    ('评估表', '$evaluation_sheet', '评[估分].{0,2}[表单]|评分|CDAI|CHA2DS2|MMSE|VTE|(指标调查|查体|营养记录|体检格式|量)表|评估工具|严重程度指数|评[估定]$'),
    ('化疗评估表', '$evaluation_sheet$chemotherapy_evaluation_sheet', '化疗评估表'),
    ('静脉血栓栓塞评估表', '$evaluation_sheet$venous_thromboembolism_evaluation_sheet', '静脉血栓栓塞评估表'),
    ('镇静镇痛记录单', '$sedation_sheet', '镇[静痛]记录单'),
    ('宣教单', '$education_list', '宣教'),
    ('治疗单', '$treatment_sheet', '治疗单'),
    ('授权委托书', '$letter_of_authorization', '授权委托书'),
    ('手术护理记录单', '$surgery_nursing_record_sheet', '手术护理记录单'),
    ('介入/特殊穿刺术后交接单', '$centesis_handoff', '介入/特殊穿刺术后交接单'),
    ('术后交接单', '$postoperative_handoff', '术后交接单'),
    ('门诊手术术中护理记录单', '$outpatient_intraoperative_nursing_record_sheet', '门诊手术术中护理记录单'),
    ('病人一般信息修改申请', '$basic_info_amendment_application', '一般信息修改申请'),
    ('手术病人术前评估', '$preoperative_assessment', '手术病人术前评估'),
    ('日间手术术前评估', '$day_surgery_preoperative_assessment', '日间手术术前评估'),
    ('审批表', '$approval_form', '审批表'),
    ('抗生素审批表', '$approval_form$antibiotic_approval_form', '抗生素审批表'),
    ('手术审批表', '$approval_form$operation_approval_form', '手术审批表'),
    ('申请单', '$application_sheet', '申请单'),
    ('输血申请单', '$application_sheet$transfusion_application_sheet', '输血申请单'),
    ('申请单', '$application_sheet$pathology_application_sheet', '申请单'),
    ('申请单', '$application_sheet', '申请单'),
    ('承诺书', '$commitment', '承诺书'),
    ('登记表', '$registration_form', '登记表'),
    ('出院证', '$discharge_card', '出院证'),
    ('诊断证明', '$diagnosis_proof', '诊断证明'),
    ('医嘱单', '$doctor_advice', '医嘱单'),
    ('长期医嘱单', '$doctor_advice$long_term_orders', '长期医嘱单'),
    ('临时医嘱单', '$doctor_advice$short_term_orders', '临时医嘱单'),
]

SAMPLE_ARCHIVE_REDIS_LIST_KEY = "qcaudit.sample.archive"

AI_DICT = {1: "AI", 0: "人工", 2: "AI"}

SAMPLE_BY_TAG = 'tag'
SAMPLE_BY_TAG_ALL = 'tags'
SAMPLE_BY_GROUP = 'group'

# dept：科室，ward：病区，attending:责任医生，branch:院区，num:总量, group:诊疗组，tag:重点病历标签）
SAMPLE_BY_DICT = {"dept": "科室", "ward": "病区", "attending": "责任医生", "branch": "院区", "num": "总量", "group": "诊疗组", "tag": "重点病历"}

# 手术切口等级
OPERATION_CUT_LEVEL = {
    '0类切口': {'0类切口', '0类', '0'},
    'I类切口': {'I类切口', 'I类', '1类', '1'},
    'II类切口': {'II类切口', 'II类', '2类', '2'},
    'III类切口': {'III类切口', 'III类', '3类', '3'},
}

# 手术愈合等级
OPERATION_HEAL_LEVEL = ['甲', '乙', '丙']

# 手术等级
OPERATION_LEVEL = {
    '无级别': {'无级别', '0'},
    '一级': {'一级', '1级', '1'},
    '二级': {'二级', '2级', '2'},
    '三级': {'三级', '3级', '3'},
    '四级': {'四级', '4级', '4'},
}

# 诊断
DIAGNOSIS_TYPE_0 = 0
# 病理诊断
DIAGNOSIS_TYPE_1 = 1
# 损伤/中毒诊断
DIAGNOSIS_TYPE_2 = 2
