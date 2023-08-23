# coding=utf-8
import argparse
import logging
import pandas as pd
from argparse import ArgumentParser

from . import QCDataBaseManager as _QCDataBaseManager

logging.basicConfig(level=logging.INFO)


class QCDataBaseManager(_QCDataBaseManager):

    def importDocuments(self, dataframe: pd.DataFrame):
        with self.session() as session:
            model = self.models['documents']
            # 获取已确认的目录排序和目录对照规则
            catalog_order = dict(default_order)
            # logging.info(session.query(model.standard_name, model.type_name, model.type_order).distinct())
            for d in session.query(model.standard_name, model.type_name, model.type_order).distinct().all():
                if not d.standard_name or not d.type_name:
                    continue
                catalog_order[d.type_name] = d.type_order
                secondary_to_standard[d.standard_name] = d.type_name
            logging.info(catalog_order)
            # 处理数据
            for idx, data in dataframe.iterrows():
                name = data['文书名称']
                standard_name = data['标准文书对照']
                # validate
                if pd.isnull(standard_name) or not standard_name:
                    logging.info(f'exception empty standard_name, column: {idx}')
                    continue
                if pd.isnull(name) or not name:
                    logging.info(f'exception empty document-name, column: {idx}')
                    continue
                # 根据文书对照关系查找一级文书名作为目录名称
                primary_name = secondary_to_standard.get(standard_name) or standard_name
                catalog = primary_name if catalog_order.get(primary_name) else '其它'
                # 查询文书对照是否存在
                document = session.query(self.models['documents']).filter_by(name=name).first()
                if not document:
                    obj = {
                        'name': name,
                        'standard_name': standard_name,
                        'index': 1000,  # 文书按时间排序顺序
                        'type': '0',  # 废弃字段
                        'type_name': catalog,
                        'type_order': catalog_order.get(catalog, 10000),  # 目录排序
                    }
                    row = self.models['documents'](**obj)
                    session.add(row)
                else:
                    document.standard_name = standard_name
                    document.type_name = catalog
                    document.type_order = catalog_order.get(catalog, 10000)

        logging.info('import finished!!')


def getArgs():
    parser = ArgumentParser(prog='文书对照表导入', description='导入文书对照关系表')
    parser.add_argument('-f', dest='file', help='上传一个文件', type=argparse.FileType(mode='r', encoding='utf-8'))
    parser.add_argument('--db-url', dest='dbUrl',
                        default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4',
                        help='数据库url, Default:%(default)s')
    return parser


def STREAMLIT_FUNCTION(args):
    if args.file:
        tmpdata = pd.read_csv(args.file.name)
        db = QCDataBaseManager(args.dbUrl)
        db.importDocuments(tmpdata)


STREAMLIT_PARSER = getArgs()

# 默认文书目录顺序
default_order = {
    '病案首页': 1,
    '入院记录': 2,
    '24小时出入院记录': 3,
    '入出院记录': 4,
    '首次病程记录': 5,
    '病程记录': 10,
    '疑难病例讨论': 15,
    '超30天病历讨论': 16,
    '危重病例讨论': 17,
    '授权委托书': 18,
    '知情选择书': 19,
    '术前讨论及术前小结': 20,
    '知情同意书': 25,
    '麻醉术前访视记录': 26,
    '麻醉术后访视记录': 27,
    '镇静镇痛记录单': 28,
    '手术风险评估记录': 29,
    '日间手术术前评估': 30,
    '手术安全核查记录': 35,
    '手术护理记录单': 36,
    '术前准备核查表': 37,
    '审批表': 38,
    '麻醉记录': 39,
    '手术记录': 40,
    '有创操作记录': 45,
    '术后交接单': 46,
    '介入/特殊穿刺术后交接单': 47,
    '出院记录': 48,
    '死亡记录': 49,
    '死亡病例讨论': 50,
    '谈话记录': 55,
    '评估表': 56,
    '登记表': 57,
    '住院证': 58,
    '出院证': 59,
    '入院须知': 60,
    '治疗单': 65,
    '宣教单': 66,
    '门诊手术术中护理记录单': 67,
    '病人一般信息修改申请': 68,
    '承诺书': 69,
    '输血申请单': 70,
    '病理申请单': 75,
    '其它': 10000,
}

# 默认二级文书名对照标准文书名
secondary_to_standard = {
    '查房记录': '病程记录',
    '上级医师查房记录': '病程记录',
    '主治医师查房记录': '病程记录',
    '主（副）任医师查房记录': '病程记录',
    '科主任查房记录': '病程记录',
    '日常查房记录': '病程记录',
    '危急值处理记录': '病程记录',
    '术前查房记录': '病程记录',
    '术后第一天查房记录': '病程记录',
    '术后第二天查房记录': '病程记录',
    '术后第三天查房记录': '病程记录',
    '术后首次病程记录': '病程记录',
    '科室大查房记录': '病程记录',
    '阶段小结': '病程记录',
    '转科记录': '病程记录',
    '转出记录': '病程记录',
    '出ICU记录': '病程记录',
    '病房转ICU记录': '病程记录',
    '转入记录': '病程记录',
    '入ICU记录': '病程记录',
    'ICU转病房记录': '病程记录',
    '转组记录': '病程记录',
    '转院记录': '病程记录',
    '输血前评估记录': '病程记录',
    '输血记录': '病程记录',
    '输血后评价记录': '病程记录',
    '会诊记录': '病程记录',
    '会诊申请': '病程记录',
    '会诊意见': '病程记录',
    '抢救记录': '病程记录',
    '交接班记录': '病程记录',
    '新生儿记录': '病程记录',
    '术前小结': '术前讨论及术前小结',
    '术前讨论': '术前讨论及术前小结',
    '非计划二次手术讨论记录': '术前讨论及术前小结',
    '手术知情同意书': '知情同意书',
    '麻醉知情同意书': '知情同意书',
    '病危（重）通知书': '知情同意书',
    '病危通知书': '知情同意书',
    '病重通知书': '知情同意书',
    '操作同意书': '知情同意书',
    '输血同意书': '知情同意书',
    '检查同意书': '知情同意书',
    '治疗同意书': '知情同意书',
    '镇静治疗同意书': '知情同意书',
    '癌痛治疗同意书': '知情同意书',
    '激素治疗同意书': '知情同意书',
    '抗凝同意书': '知情同意书',
    '自费药物同意书': '知情同意书',
    '死亡告知书': '知情同意书',
    '自动出院告知书': '知情同意书',
    '静脉血栓形成告知书': '知情同意书',
    '手术病人术前评估': '日间手术术前评估',
    '抗生素审批表': '审批表',
    '手术审批表': '审批表',
    '重大疑难手术审批报告': '审批表',
    '清宫手术记录': '手术记录',
    '母婴同室新生儿出院记录': '出院记录',
    '24小时入院死亡记录': '死亡记录',
    '术前谈话记录': '谈话记录',
    '术后谈话记录': '谈话记录',
    '入院七十二小时谈话记录': '谈话记录',
    '入ICU谈话记录': '谈话记录',
    '五日未手术谈话记录': '谈话记录',
    '化疗评估表': '评估表',
    '静脉血栓栓塞评估表': '评估表',
}
