import streamlit as st
import argparse
from argparse import ArgumentParser
import logging
import pandas as pd
from .qcdatabase import QCDataBaseManager
import pika
import json
import time


required_columns = ['值域编码', '值域名称', '值域编码1', '值域名称1']

medical_advice_type = ['医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']


class RabbitMQ:

	def __init__(self, url):
		self.url = url
		self.connect()

	def connect(self):
		self.connection = pika.BlockingConnection(
			pika.URLParameters(self.url)
		)
		self.channel = self.connection.channel()

	def publish(self, message: dict, exchange='qcetl', routing_key=''):
		"""发送消息

		Args:
			message (dict): [description]
			exchange (str, optional): [description]. Defaults to 'qcetl'.
		"""
		try:
			self.channel.basic_publish(
				exchange=exchange,
				routing_key=routing_key or message['type'],
				body=json.dumps(message, ensure_ascii=False),
				properties=pika.BasicProperties(
					delivery_mode=2
				)
			)
		except pika.exceptions.AMQPConnectionError as e:
			logging.exception(e)
			time.sleep(0.1)
			self.connect()
			self.publish(message, exchange, routing_key)


def compare_data(code, name, items, data_frame, type_name=None, session=None, db_obj=None):
	if type_name == '文书':
		model = db_obj.models['documents']
		catalog_order = dict(default_order)
		for item in items:
			if not item.standard_name or not item.type_name:
				continue
			catalog_order[item.type_name] = item.type_order
			secondary_to_standard[item.standard_name] = item.type_name
		logging.info(catalog_order)
		for idx, data in data_frame.iterrows():
			name = data['值域名称']
			standard_name = data['值域名称1']
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
			document = session.query(model).filter_by(name=name).first()
			if not document:
				obj = {
					'name': name,
					'standard_name': standard_name,
					'index': 1000,  # 文书按时间排序顺序
					'type': '0',  # 废弃字段
					'type_name': catalog,
					'type_order': catalog_order.get(catalog, 10000),  # 目录排序
				}
				row = model(**obj)
				session.add(row)
			else:
				document.standard_name = standard_name
				document.type_name = catalog
				document.type_order = catalog_order.get(catalog, 10000)
		return True
	for item in items:
		code_v = getattr(item, code)
		name_v = getattr(item, name)
		result = data_frame.loc[(data_frame['值域编码'] == code_v) & (data_frame["值域名称"] == name_v)]
		if not result.empty:
			item.std_code = result["值域编码1"].iloc[0]
			item.std_name = result["值域名称1"].iloc[0]
	return True

def compare_checkout_data(session, data_frame, db):
	content_model = db.models['labContent']
	model = db.models['labInfo']
	items = session.query(content_model, model.specimen) \
				.join(model, content_model.reportId == model.id) \
				.filter(content_model.itemname != None) \
				.all()
	for item in items:
		code_v = item.specimen + item[0].itemname
		name_v = item[0].itemname
		result = data_frame.loc[(data_frame['值域编码'] == code_v) & (data_frame["值域名称"] == name_v)]
		if not result.empty:
			item[0].std_code = result["值域编码1"].iloc[0]
			item[0].std_name = result["值域名称1"].iloc[0]

def update_normal_dict(model, session, name, data_frame):
	type_dict = {
		'手术': 'fp_operation',
		'诊断': 'fp_diagnosis',
		'检验': 'labitem',
	}
	item_type = type_dict.get(name)
	if name in medical_advice_type:
		item_type = 'order'
	if not item_type:
		return
	normal_item = session.query(model).filter(model.item_type == item_type).all()
	normal_item_dict = {(item.original_code, item.original_name): item for item in normal_item}
	for index, row in data_frame.iterrows():
		normal_obj = normal_item_dict.get((row['值域编码'], row['值域名称']), None)
		if not row['值域编码1'] or not row['值域名称1']:
			continue
		if normal_obj:
			normal_obj.std_name = row['值域名称1']
			normal_obj.std_code = row['值域编码1']
		else:
			item = model(
				original_code=row['值域编码'],
				original_name=row['值域名称'],
				std_code=row['值域编码1'],
				std_name=row['值域名称1'],
				item_type=item_type
			)
			session.add(item)
			normal_item_dict[(row['值域编码'], row['值域名称'])] = item

def get_compare_data(name, data_frame, url):
	db = QCDataBaseManager(url)
	with db.session() as session:
		s_code, s_name, model = '', '', ''
		if name in medical_advice_type:
			model = db.models['medicalAdvice']
			_n = name.split('-')[1]
			if '药' in _n:
				items = session.query(model).filter(model.order_flag.like('%药%')).all()
			else:
				items = session.query(model).filter(model.order_flag == _n).all()
			s_code, s_name = 'code', 'name'
			compare_data(s_code, s_name, items, data_frame)
			model = db.models['normal_dict']
			update_normal_dict(model, session, name, data_frame)
			return True
		if name == "检验":
			compare_checkout_data(session, data_frame, db)
			model = db.models['normal_dict']
			update_normal_dict(model, session, name, data_frame)
			return True
		if name == "检查":
			model = db.models['examContent']
			s_code, s_name = 'itemname', 'itemname'
		if name == "手术":
			model = db.models['fpoperation']
			s_code, s_name = 'oper_code', 'oper_name'
		if name == "诊断":
			model_1 = db.models['fpdiagnosis']
			model_2 = db.models['mz_diagnosis']
			items_1 = session.query(model_1).all()
			items_2 = session.query(model_2).all()
			compare_data('icdcode', 'icdname', items_1, data_frame)
			compare_data('code', 'name', items_2, data_frame)
			model = db.models['normal_dict']
			update_normal_dict(model, session, name, data_frame)
			return True
		if name == "科室":
			model = db.models['department']
			s_code, s_name = 'code', 'name'
		if name == '文书':
			model = db.models['documents']
			s_code, s_name = 'documentName', 'documentName'
			items = session.query(model.standard_name, model.type_name, model.type_order).distinct().all()
			compare_data(s_code, s_name, items, data_frame, name, session, db)
			return True
		items = session.query(model).all()
		compare_data(s_code, s_name, items, data_frame)
		# 更新normal_dict
		if name == '手术':
			model = db.models['normal_dict']
			update_normal_dict(model, session, name, data_frame)
		return True


def getArgs():
	choices = ['诊断', '手术', '文书', '检验', '检查', '病理', '科室', '医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']
	parser = ArgumentParser(prog='导入标准字典到院内', description='导入标准字典到院内')
	parser.add_argument('-f', dest='file', help='标准字典文件', type=argparse.FileType(mode='rb'))
	parser.add_argument('--dict-name', dest='name', help='选择上传的类型',
						choices=choices, required=True)
	parser.add_argument('--sql-url', dest='dburl', default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4', help='数据库地址', required=True)
	parser.add_argument('--mq-url', dest='mqurl', default='amqp://rxthinking:gniknihtxr@rabbitmq.infra-default:42158/%2F', help='rabbitmq地址', required=True)

	return parser


def process(args):
	name = args.name
	file_obj = args.file
	data_frame = pd.read_excel(file_obj.read(), converters={'值域编码': str, "值域编码1": str}, keep_default_na=False)
	columns = data_frame.columns
	for rc in required_columns:
		if rc not in columns:
			st.error("表中必须存在的列为:['值域编码', '值域名称', '值域编码1', '值域名称1']")
			return
	data_frame.drop_duplicates(subset=["值域编码", "值域名称"], keep='first', inplace=True)
	st.write(data_frame)
	try:
		get_compare_data(name, data_frame, args.dburl)
		if name in medical_advice_type or name == '诊断' or name == '手术' or name == '检验':
			# 发送重启字典消息
			mq = RabbitMQ(args.mqurl)
			message = {
				'type': 'qc.dict.reload',
				'body': {}
			}
			mq.publish(message)
		st.success("导入对照成功")
	except Exception as e:
		st.error(e)



# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getArgs()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process

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
