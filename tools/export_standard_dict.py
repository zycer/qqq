import io
import itertools
from argparse import ArgumentParser
import streamlit as st
from .qcdatabase import QCDataBaseManager
import pandas as pd
from sqlalchemy import distinct
import os

path = '/tmp/'


medical_advice_type = ['医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']

@st.cache
def select_dict_data(name):
	url = 'mysql+pymysql://root:rxthinkingmysql@192.168.101.155:49138/cdss_qcmanager?charset=utf8mb4'
	db = QCDataBaseManager(url)
	data = list()
	with db.session() as session:
		if name in medical_advice_type:
			_n = name.split('-')[1]
			model = db['medicalAdvice']
			if '药' in _n:
				items = session.query(model.code, model.name).filter(model.order_flag.like('%药%')).distinct().all()
			else:
				items = session.query(model.code, model.name).filter(model.order_flag == _n).distinct().all()
			for item in items:
				data.append({"值域编码": item.code, "值域名称": item.name})
		if name == "检验":
			model = db['labInfo']
			content_model = db['labContent']
			items = session.query(content_model, model).join(model, content_model.reportId == model.id).all()
			for item in items:
				content, info = item[0], item[1]
				tmp = {"值域编码": content.code, "值域名称": content.itemname, "单位": content.unit, "范围值": content.valrange,
					   "套餐名称": info.testname, "样本": info.specimen}
				data.append(tmp)
		if name == "检查":
			model = db['examInfo']
			content_model = db['examContent']
			items = session.query(content_model, model).join(model, content_model.reportId == model.id).all()
			for item in items:
				content, info = item[0], item[1]
				tmp = {"值域编码": content.itemname, "值域名称": content.itemname, "套餐名称": info.examname, "检查类型": info.examtype}
				data.append(tmp)
		if name == "手术":
			model = db['fpoperation']
			items = session.query(model.oper_code, model.oper_name).distinct().all()
			for item in items:
				data.append({"值域编码": item.oper_code, "值域名称": item.oper_name})
		if name == "诊断":
			model_1 = db['fpdiagnosis']
			model_2 = db['mz_diagnosis']
			items_1 = session.query(model_1.icdcode.label('code'), model_1.icdname.label('name')).distinct().all()
			items_2 = session.query(model_2.code, model_2.name).distinct().all()
			for item in itertools.chain(items_1, items_2):
				tmp = {"值域编码": item.code, "值域名称": item.name}
				data.append(tmp)
		if name == "科室":
			model = db['department']
			items = session.query(model.code, model.name).distinct().all()
			for item in items:
				data.append({"值域编码": item.code, "值域名称": item.name})
	return data


def getArgs():
	choices = ['诊断', '手术', '检验', '检查', '病理', '科室', '医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']
	parse = ArgumentParser(prog='导出院内字典', description='### 导出未对照的文书名称并给出自动对照结果')
	parse.add_argument('--dict-name', dest='name', help='选择下载的类型',
					   choices=choices, required=True)
	return parse


def process(args):
	data = select_dict_data(args.name)
	data_frame = pd.DataFrame(data)
	data_frame.drop_duplicates(subset=["值域编码", "值域名称"], keep='first', inplace=True)
	st.write(data_frame)
	excel_path = os.path.join(path, args.name + '.xlsx')
	data_frame.to_excel(excel_path, index=False)
	with open(excel_path, "rb") as file:
		st.download_button(
			label=args.name + "字典下载",
			data=file,
			file_name=args.name + ".xlsx",
			mime="text/excel",
			help='点击下载字典文件'
		)


# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getArgs()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process
