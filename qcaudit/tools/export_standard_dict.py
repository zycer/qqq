import io
import itertools
from argparse import ArgumentParser
import streamlit as st
from .qcdatabase import QCDataBaseManager
import pandas as pd
from sqlalchemy import distinct, func
import os

path = '/tmp/'


medical_advice_type = ['医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']

def select_dict_data(name, url):
	db = QCDataBaseManager(url)
	data = list()
	with db.session() as session:
		count = func.count('*').label('count')
		if name in medical_advice_type:
			_n = name.split('-')[1]
			model = db.models['medicalAdvice']
			if '药' in _n:
				items = session.query(model.code, model.name, count).filter(model.order_flag == '药品',
																			model.code is not None,
																			model.name is not None).group_by(
					model.code, model.name).having(count >= 10).order_by(count.desc()).all()
			else:
				items = session.query(model.code, model.name, count).filter(model.order_flag == _n,
																			model.code is not None,
																			model.name is not None).group_by(
					model.code, model.name).having(count >= 10).order_by(count.desc()).all()
			for item in items:
				data.append({"值域编码": item.code, "值域名称": item.name, "频次": item.count})
		if name == "检验":
			model = db.models['labInfo']
			content_model = db.models['labContent']
			items = session.query(content_model.code, content_model.itemname, content_model.unit,
								  content_model.valrange,
								  model.testname, model.specimen, count) \
				.join(model, content_model.reportId == model.id) \
				.group_by(content_model.code, content_model.itemname, content_model.unit, content_model.valrange,
						  model.testname, model.specimen) \
				.having(count > 10) \
				.all()
			for item in items:
				tmp = {"值域编码": item.specimen+item.itemname, "值域名称": item.itemname, "单位": item.unit, "范围值": item.valrange,
					   "套餐名称": item.testname, "样本": item.specimen,"频次":item.count}
				data.append(tmp)
		if name == "检查":
			model = db.models['examInfo']
			content_model = db.models['examContent']
			items = session.query(content_model.itemname, model.examname, model.examtype, count) \
				.join(model, content_model.reportId == model.id) \
				.group_by(content_model.itemname, model.examname, model.examtype) \
				.having(count > 10) \
				.all()
			for item in items:
				tmp = {"值域编码": item.itemname, "值域名称": item.itemname, "套餐名称": item.examname, "检查类型": item.examtype,
					   "频次": item.count}
				data.append(tmp)
		if name == "手术":
			model = db.models['fpoperation']
			items = session.query(model.oper_code, model.oper_name, count).filter(model.oper_code is not None,
																				  model.oper_name is not None).group_by(
				model.oper_code, model.oper_name).having(count >= 10).order_by(count.desc()).all()
			for item in items:
				data.append({"值域编码": item.oper_code, "值域名称": item.oper_name, "频次": item.count})
		if name == "诊断":
			model_1 = db.models['fpdiagnosis']
			model_2 = db.models['mz_diagnosis']
			items_1 = session.query(model_1.icdcode.label('code'), model_1.icdname.label('name'), count).filter(
				model_1.icdcode is not None, model_1.icdname is not None).group_by(
				model_1.icdcode, model_1.icdname).having(count >= 10).order_by(count.desc()).all()

			items_2 = session.query(model_2.code, model_2.name, count).filter(model_2.code is not None,
																	   model_2.name is not None).group_by(
				model_2.code, model_2.name).having(count >= 10).order_by(count.desc()).all()
			for item in itertools.chain(items_1, items_2):
				if not item.code:
					continue
				tmp = {"值域编码": item.code, "值域名称": item.name, "频次": item.count}
				data.append(tmp)
		if name == "科室":
			model = db.models['department']
			items = session.query(model.code, model.name).distinct().all()
			for item in items:
				data.append({"值域编码": item.code, "值域名称": item.name})
		if name == '文书':
			model = db.models['emrInfo']
			items = session.query(model.documentName, count).group_by(model.documentName).having(count>10).order_by(count.desc()).all()
			for item in items:
				data.append({"值域编码": item.documentName, "值域名称": item.documentName, "频次": item.count})
	return data


def getArgs():
	choices = ['诊断', '手术', '检验', '检查', '文书', '病理', '科室', '医嘱-检验', '医嘱-检查', '医嘱-药品', '医嘱-手术']
	parse = ArgumentParser(prog='导出院内字典', description='### 导出未对照的文书名称并给出自动对照结果')
	parse.add_argument('--dict-name', dest='name', help='选择下载的类型',
					   choices=choices, required=True)
	parse.add_argument('--sql-url', dest='dburl', default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4', help='数据库地址', required=True)
	return parse


def process(args):
	data = select_dict_data(args.name, args.dburl)
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
