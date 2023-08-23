import streamlit as st
import argparse
from argparse import ArgumentParser
import pandas as pd
from .qcdatabase import QCDataBaseManager


required_columns = ['值域编码', '值域名称', '值域编码1', '值域编码2']

medical_advice_type = ['医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']


def compare_data(code, name, items, data_frame):
	for item in items:
		code_v = getattr(item, code)
		name_v = getattr(item, name)
		result = data_frame.loc[(data_frame['值域编码'] == code_v) & (data_frame["值域名称"] == name_v)]
		if not result.empty:
			item.std_code = result["值域编码1"]
			item.std_name = result["值域名称1"]
	return True

def get_compare_data(name, data_frame):
	url = 'mysql+pymysql://root:rxthinkingmysql@192.168.101.155:49138/cdss_qcmanager?charset=utf8mb4'
	db = QCDataBaseManager(url)
	with db.session() as session:
		s_code, s_name, model = '', '', ''
		if name in medical_advice_type:
			model = db['medicalAdvice']
			_n = name.split('-')[1]
			if '药' in _n:
				items = session.query(model).filter(model.order_flag.like('%药%')).all()
			else:
				items = session.query(model).filter(model.order_flag == _n).all()
			s_code, s_name = 'code', 'name'
			compare_data(s_code, s_name, items, data_frame)
			return True
		if name == "检验":
			model = db['labContent']
			s_code = 'code'
			s_name = 'itemname'
		if name == "检查":
			model = db['examContent']
			s_code, s_name = 'itemname'
		if name == "手术":
			model = db['fpoperation']
			s_code, s_name = 'oper_code', 'oper_name'
		if name == "诊断":
			model_1 = db['fpdiagnosis']
			model_2 = db['mz_diagnosis']
			items_1 = session.query(model_1).all()
			items_2 = session.query(model_2).all()
			compare_data('icdcode', 'icdname', items_1, data_frame)
			compare_data('code', 'name', items_2, data_frame)
			return True
		if name == "科室":
			model = db['department']
			s_code, s_name = 'code', 'name'
		items = session.query(model).all()
		compare_data(s_code, s_name, items, data_frame)
		return True


def getArgs():
	choices = ['诊断', '手术', '检验', '检查', '病理', '科室', '医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']
	parser = ArgumentParser(prog='导入标准字典到院内', description='导入标准字典到院内')
	parser.add_argument('-f', dest='file', help='标准字典文件', type=argparse.FileType(mode='rb'))
	parser.add_argument('--dict-name', dest='name', help='选择上传的类型',
						choices=choices, required=True)

	return parser


def process(args):
	name = args.name
	file_obj = args.file
	data_frame = pd.read_excel(file_obj.read())
	columns = data_frame.columns
	for rc in required_columns:
		if rc not in columns:
			st.error("表中必须存在的列为:['值域编码', '值域名称', '值域编码1', '值域编码2']")
			return
	data_frame.drop_duplicates(subset=["值域编码", "值域名称"], keep='first', inplace=True)
	st.write(data_frame)
	try:
		get_compare_data(name, data_frame)
		st.success("导入对照成功")
	except Exception as e:
		st.error(e)



# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getArgs()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process
