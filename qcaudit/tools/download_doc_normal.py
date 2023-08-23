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


doc_types_data = [
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
    ('死亡病例讨论', '$death_discussion', '死亡病例讨论'),
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

doc_list = [item[0] for item in doc_types_data]
view_doc_list = ["全部文书"] + doc_list


def getArgs():
    parser = ArgumentParser(prog='结构化标准文书导出-文书', description='### 结构化标准文书导出-文书')
    parser.add_argument('--db-host', dest='dbHost', default="mysql.infra-default", help='数据库HOST')
    parser.add_argument('--db-port', dest='dbPort', default="3306", help='数据库PORT')
    parser.add_argument('--db-db', dest='dbDb', default="qcmanager", help='数据库DB')
    parser.add_argument('--doc-list', dest='docList', help='标准文书列表', nargs='*', default=["全部文书"], choices=view_doc_list)
    parser.add_argument('--doc-num', dest='docNum', default=1, help='指定文书提取数', type=int)
    return parser


def process(args):
    start_time = time.time()
    db_url = 'mysql+pymysql://root:rxthinkingmysql@{h}:{p}/{d}?charset=utf8mb4'.format(h=args.dbHost, p=args.dbPort, d=args.dbDb)
    db = QCDataBaseManager(db_url)
    doc_data = []
    with db.session() as s:
        documents = db.models["documents"]
        query_normal = s.query(documents).all()
        normal_dict = {item.name: item.standard_name for item in query_normal}
        req_doc_list = args.docList
        if "全部文书" in req_doc_list:
            req_doc_list = doc_list
        docs = ",".join(['"%s"' % item for item in req_doc_list])
        query_exist_doc_sql = '''select d.standard_name, ei.documentName, count(ei.id) from `emrInfo` ei inner join documents d on ei.`documentName` = d.name where d.standard_name in (%s) group by d.standard_name, ei.documentName;''' % docs
        logger.info("query_exist_doc_sql: %s", query_exist_doc_sql)
        query_exist_doc = s.execute(query_exist_doc_sql)
        exist_doc_data = query_exist_doc.fetchall()
        logger.info("exist_doc_data: %s", exist_doc_data)
        doc_num_dict = {}
        for item in exist_doc_data:
            if not doc_num_dict.get(item[0], 0):
                doc_num_dict[item[0]] = 0
            doc_num_dict[item[0]] += item[2]
        logger.info("doc_num_dict: %s", doc_num_dict)
        no_exist_doc = []
        arg_doc_list = []
        less_doc_list = []
        for doc in req_doc_list:
            if doc_num_dict.get(doc, 0) > 0:
                arg_doc_list.append(doc)
                if doc_num_dict[doc] < args.docNum:
                    less_doc_list.append(doc)
                continue
            no_exist_doc.append(doc)
        if no_exist_doc:
            print("[%s] 文书无数据" % ",".join(no_exist_doc))
        if less_doc_list:
            print("[%s] 文书存在数据小于%s" % (",".join(less_doc_list), args.docNum))
        logger.info("arg_doc_list: %s", arg_doc_list)

        for doc in arg_doc_list:
            query_sql = '''select ei.caseId, ei.docId, ei.documentName, ec.contents, ec.htmlContent, ei.createTime, ei.recordTime, ei.updateTime from emrInfo ei inner join emrContent ec on ei.emrContentId = ec.id inner join documents d on ei.documentName = d.name where d.standard_name = "%s" and ec.htmlContent != "" order by ei.id desc limit %s;''' % (doc, args.docNum)
            query = s.execute(query_sql)
            data = query.fetchall()
            logger.info("doc: %s, queryset len: %s", doc, len(data))
            for item in data:
                create_time = item[5].strftime("%Y-%m-%d %H:%M:%S") if item[5] else ""
                record_time = item[6].strftime("%Y-%m-%d %H:%M:%S") if item[6] else ""
                update_time = item[7].strftime("%Y-%m-%d %H:%M:%S") if item[7] else ""
                tmp = {"caseId": item[0], "docId": item[1], "documentName": item[2].strip(),
                       "contents": item[3],
                       "normalName": normal_dict.get(item[2].strip(), item[2].strip()),
                       "htmlContent": item[4], "createTime": create_time, "recordTime": record_time, "updateTime": update_time}
                doc_data.append(tmp)
    with open("/tmp/doc_normal.txt", "wb") as f:
        for item in doc_data:
            f.write(json.dumps(item, ensure_ascii=False).encode())
            f.write(b"\n")
    with open("/tmp/doc_normal.txt", "rb") as f:
        data = f.read()
    st.download_button('下载', data=data, file_name='结构化文书.txt', help='点击下载')
    end_time = time.time()
    logger.info("end, use: %s", end_time - start_time)
    return ""


# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getArgs()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process

