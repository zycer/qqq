#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: towebconfig.py
@time: 2021/12/10 11:21 上午
@desc:
"""

# 专家统计-全院成绩统计
EXPERT_ALL_SCORE_YAML = '''
name: test
fields:
    - name: 平均分
    - name: 总数
    - name: {first}率
    - name: {second}率
    - name: {third}率
    - name: {first}数
    - name: {second}数
    - name: {third}数
groupFields:
    - name: 院区
'''

# 专家统计-全院成绩统计-基础结构
EXPERT_ALL_SCORE_DATA = {"院区": "", "平均分": "", "总数": ""}

# 专家统计-甲/乙/丙级基础结构
EXPERT_LEVEL_DATA_1 = {"甲级率": "", "乙级率": "", "丙级率": "", "甲级数": 0, "乙级数": 0, "丙级数": 0}
# 专家统计-优秀/合格/不合格基础结构
EXPERT_LEVEL_DATA_2 = {"优秀率": "", "合格率": "", "不合格率": "", "优秀数": 0, "合格数": 0, "不合格数": 0}
# 专家统计-不排序字段
EXPERT_NO_SORT_FIELD = ["甲级率", "乙级率", "丙级率", "优秀率", "合格率", "不合格率", "内外科", "病区", "科室"]

# 内外科成绩分析-查询配置
INTERNAL_SURGERY_LIST_YAML = '''
name: test
fields:
    - name: 总分
      hide: true
    - name: 总数
      hide: true
    - name: 平均分
      ignoreAcc: true
      formular: '{总分}*1.0/{总数}'
      format: '%0.1f'
    - name: [first]率
      formular: '{[first]数}*1.0/{总数}*100'
      format: '%0.1f%%'
      ignoreAcc: true
    - name: [second]率
      formular: '{[second]数}*1.0/{总数}*100'
      format: '%0.1f%%'
      ignoreAcc: true
    - name: [third]率
      formular: '{[third]数}*1.0/{总数}*100'
      format: '%0.1f%%'
      ignoreAcc: true
    - name: [first]数
    - name: [second]数
    - name: [third]数
groupFields:
    - name: 内外科
      mergeCells: true
      addAccRow: true
      accRowFirst: true
    - name: [ward]
      addAccRow: true
      mergeCells: true
      accRowFirst: true
'''

# 内外科成绩分析-查询-基础结构
INTERNAL_SURGERY_LIST_DATA = {"内外科": "", "平均分": ""}

# 医生成绩统计-查询配置
DOCTOR_SCORE_LIST_YAML = '''
name: test
fields:
    - name: 总分
      hide: true
    - name: 平均分
      ignoreAcc: true
      formular: '{总分}*1.0/{总数}'
      format: '%0.1f'
    - name: 总数
    - name: [first]率
      formular: '{[first]数}*1.0/{总数}*100'
      format: '%0.1f%%'
      ignoreAcc: true
    - name: [second]率
      formular: '{[second]数}*1.0/{总数}*100'
      format: '%0.1f%%'
      ignoreAcc: true
    - name: [third]率
      formular: '{[third]数}*1.0/{总数}*100'
      format: '%0.1f%%'
      ignoreAcc: true
    - name: [first]数
    - name: [second]数
    - name: [third]数
groupFields:
    - name: [ward]
      addAccRow: true
      mergeCells: true
      accRowFirst: true
    - name: 诊疗小组
      addAccRow: true
      mergeCells: true
      accRowFirst: true
    - name: 医生姓名
      addAccRow: true
      mergeCells: true
      accRowFirst: true
'''

# 专家统计-科室成绩统计明细配置
EXPERT_DEPARTMENT_DETAIL_YAML = '''
name: test
fields:
    - name: 平均分
    - name: 总数
    - name: [first]率
    - name: [second]率
    - name: [third]率
    - name: [first]数
    - name: [second]数
    - name: [third]数
groupFields:
    - name: 时间
      addAccRow: false
      accRowFirst: false
'''

# 专家统计-科室成绩统计明细基础数据
EXPERT_DEPARTMENT_DETAIL_DATA = {"时间": "", "平均分": "", "总数": ""}

# 医生成绩统计-查询-基础结构
DOCTOR_SCORE_LIST_DATA = {"诊疗小组": "", "医生姓名": "", "平均分": "", "总数": 0, "总分": 0}

# 抽取历史导出配置
SAMPLE_HISTORY_EXPORT_YAML = '''
name: test
fields:
    - name: 问题描述
    - name: 病案扣分
    - name: 首页扣分
groupFields:
    - name: 重点病历
    - name: 问题数
    - name: {patient_name}
      mergeCells: true
    - name: 姓名
      mergeCells: true
    - name: 科室
      mergeCells: true
    - name: 病区
      mergeCells: true
    {group}
    - name: 入院日期
      mergeCells: true
    - name: 出院日期
      mergeCells: true
    - name: 住院天数
      mergeCells: true
    - name: 责任医生
      mergeCells: true
    - name: 分配医生
      mergeCells: true
    - name: 质控医生
      mergeCells: true
    - name: 质控日期
      mergeCells: true
'''

# 抽取历史诊疗组导出配置
SAMPLE_HISTORY_GROUP_EXPORT_YAML = '''- name: 诊疗组
      mergeCells: true
'''

# 抽取历史导出配置基础结构
SAMPLE_HISTORY_EXPORT_DATA = {"重点病历": "", "问题数": "", "姓名": "", "科室": "", "病区": "", "入院日期": "", "出院日期": "",
                              "住院天数": "", "责任医生": "", "分配医生": "", "质控医生": "", "质控日期": "", "问题描述": "", "病案扣分": "",
                              "首页扣分": "", "诊疗组": ""}

# 质控列表导出明细基础待拼接起始配置
QC_LIST_EXPORT_TITLE_START_YAML = '''
name: test
fields:'''

# 质控列表导出明细基础待拼接截止配置
QC_LIST_EXPORT_TITLE_END_YAML = '''
    - name: dischargeTime
      hide: true
    - name: admitTime
      hide: true
    - name: auditTime
      hide: true
    - name: receiveTime
      hide: true
    - name: 问题描述
      hide: {is_hide_1}
    - name: 病案扣分
      hide: {is_hide_2}
    - name: 首页扣分
      hide: {is_hide_3}
groupFields:'''

# 质控列表导出明细配置
QC_LIST_EXPORT_YAML = '''
name: test
fields:
    - name: 问题数
    - name: 分数
    - name: {patient_name}
    - name: 姓名
    - name: 科室
    - name: 病区
    {group}
    - name: 入院日期
    - name: 出院日期
      hide: {is_active}
    - name: 住院天数'''

# 质控列表导出明细 事中 疾病手术等字段
QC_LIST_EXPORT_ACTIVE_DIAG_YAML = '''
    - name: 疾病
    - name: 手术
    - name: 手术后天数
    - name: 费用'''

# 质控列表导出明细责任医生
QC_LIST_EXPORT_ATTEND_DOCTOR_YAML = '''
    - name: 责任医生'''

# 质控列表导出明细拼接结尾配置
QC_LIST_EXPORT_END_YAML = '''
    - name: dischargeTime
      hide: true
    - name: admitTime
      hide: true
    - name: auditTime
      hide: true
    - name: receiveTime
      hide: true
    - name: 问题描述
      hide: {is_hide_1}
    - name: 病案扣分
      hide: {is_hide_2}
    - name: 首页扣分
      hide: {is_hide_3}'''

# 有抽取质控列表导出增加配置
QC_LIST_HAVE_SAMPLE_YAML = '''
    - name: 分配医生
    - name: 质控医生
    - name: 质控日期'''

# 无抽取质控列表导出增加配置
QC_LIST_NO_SAMPLE_YAML = '''
    - name: 质控医生
    - name: 质控日期'''

# 质控列表导出明细拼接人工问题信息
QC_LIST_ACTIVE_PROBLEM_INFO_YAML = '''
    - name: 质控次数
    - name: 人工问题数
    - name: 人工问题状态'''

# 审核列表导出配置
QC_LIST_IS_RECHECK_YAML = '''
    - name: 审核人
    - name: 审核日期
    - name: 签收日期
    - name: 状态
    - name: 返修次数'''

# 质控列表导出配置
QC_LIST_NO_RECHECK_YAML = '''
    - name: 签收日期
    - name: 状态
    - name: 返修次数'''

# 单病种-科室分析病种分析公共明细配置
SINGLE_DISEASE_DEPARTMENT_SAME_YAML = '''
    - name: 应上报实上报率
    - name: 应上报实上报率_sort
      hide: true
    - name: 已取消病例
    - name: 已取消病例_sort
      hide: true
    - name: 待提交病例
    - name: 待提交病例_sort
      hide: true
    - name: 待审核病例
    - name: 待审核病例_sort
      hide: true
    - name: 待上报病例
    - name: 待上报病例_sort
      hide: true
    - name: 上报失败病例
    - name: 上报失败病例_sort
      hide: true
    - name: 上报成功病例
    - name: 上报成功病例_sort
      hide: true
    - name: 上报成功率
    - name: 上报成功率_sort
      hide: true
    - name: 例均填表耗时（单位：天）
    - name: 例均填表耗时（单位：天）_sort
      hide: true
    - name: 例均出院-上报耗时（单位：天）
    - name: 例均出院-上报耗时（单位：天）_sort
      hide: true
    - name: 按时提交病例
    - name: 按时提交病例_sort
      hide: true
    - name: 延时提交病例
    - name: 延时提交病例_sort
      hide: true
    - name: 按时提交率
    - name: 按时提交率_sort
      hide: true
    - name: 延时提交率
    - name: 延时提交率_sort
      hide: true
    - name: 按时审核病例
    - name: 按时审核病例_sort
      hide: true
    - name: 延时审核病例
    - name: 延时审核病例_sort
      hide: true
    - name: 按时审核率
    - name: 按时审核率_sort
      hide: true
    - name: 延时审核率
    - name: 延时审核率_sort
      hide: true
    - name: 按时上报病例
    - name: 按时上报病例_sort
      hide: true
    - name: 延时上报病例
    - name: 延时上报病例_sort
      hide: true
    - name: 按时上报率
    - name: 按时上报率_sort
      hide: true
    - name: 延时上报率
    - name: 延时上报率_sort
      hide: true
    - name: 机器获取数据项
    - name: 机器获取数据项_sort
      hide: true
    - name: 机器填报率
    - name: 机器填报率_sort
      hide: true
    - name: 人工填报数据项
    - name: 人工填报数据项_sort
      hide: true
    - name: 人工填表率
    - name: 人工填表率_sort
      hide: true
'''

# 单病种-病种分析统计明细配置
SINGLE_DISEASE_ANALYSE_YAML = '''
name: test
fields:
    - name: 病种名称
    - name: 单病种病例
    - name: 单病种病例_sort
      hide: true
    {}
groupFields:
    - name: 病种简称
'''.format(SINGLE_DISEASE_DEPARTMENT_SAME_YAML)

# 单病种-科室分析统计明细配置
SINGLE_DISEASE_DEPARTMENT_ANALYSE_YAML = '''
name: test
fields:
    - name: 科室名称
    - name: 覆盖病种数
    - name: 覆盖病种数_sort
      hide: true
    - name: 上报病种数
    - name: 上报病种数_sort
      hide: true
    - name: 单病种病例
    - name: 单病种病例_sort
      hide: true
    {}
groupFields:
    - name: 科室编码
'''.format(SINGLE_DISEASE_DEPARTMENT_SAME_YAML)

# 单病种-医生上报分析统计明细配置
SINGLE_DISEASE_DOCTOR_ANALYSE_YAML = '''
name: test
fields:
    - name: 医生姓名
    - name: 科室编码
    - name: 科室名称
    - name: 覆盖病种数
    - name: 覆盖病种数_sort
      hide: true
    - name: 上报病种数
    - name: 上报病种数_sort
      hide: true
    - name: 单病种病例
    - name: 单病种病例_sort
      hide: true
    {}
groupFields:
    - name: 医生编码
'''.format(SINGLE_DISEASE_DEPARTMENT_SAME_YAML)

# 单病种-填报员上报分析统计配置明细
SINGLE_DISEASE_MEMBER_ANALYSE_YAML = '''
name: test
fields:
    - name: 填报员名称
    - name: 所在科室编码
    - name: 所在科室名称
    - name: 覆盖病种数
    - name: 覆盖病种数_sort
      hide: true
    - name: 上报病种数
    - name: 上报病种数_sort
      hide: true
    - name: 单病种病例
    - name: 单病种病例_sort
      hide: true
    {}
groupFields:
    - name: 填报员编码
'''.format(SINGLE_DISEASE_DEPARTMENT_SAME_YAML)

# 单病种-审核员上报分析统计配置明细
SINGLE_DISEASE_AUDITOR_ANALYSE_YAML = '''
name: test
fields:
    - name: 审核员名称
    - name: 所在科室编码
    - name: 所在科室名称
    - name: 覆盖病种数
    - name: 覆盖病种数_sort
      hide: true
    - name: 上报病种数
    - name: 上报病种数_sort
      hide: true
    - name: 单病种病例
    - name: 单病种病例_sort
      hide: true
    {}
groupFields:
    - name: 填报员编码
'''.format(SINGLE_DISEASE_DEPARTMENT_SAME_YAML)

# 单病种-指标详情-覆盖病种数配置-覆盖病种数
SINGLE_DISEASE_QC_ANALYSE_1 = '''
name: test
fields:
    - name: 病种简称
    - name: 病种名称
    - name: 单病种病例
    - name: 上报成功
    - name: 应上报实上报率
groupFields:
    - name: 病种分类
'''

# 单病种-指标详情-覆盖病种数配置-单位为例/单位为%指标
SINGLE_DISEASE_QC_ANALYSE_2 = '''
name: test
fields:
    - name: 就诊号
    - name: 科室
    - name: 患者
    - name: 离院时间
    - name: 病种分类
groupFields:
    - name: 就诊类型
'''

# 单病种-质控统计-科室分析-医生分析-相同部分
SINGLE_DISEASE_QC_SAME_YAML = '''
    - name: 覆盖病种数
      format: '%.f'
    - name: 覆盖病种数_sort
      hide: true
    - name: 全部患者病例数
      format: '%.f例'
    - name: 全部患者病例数_sort
      hide: true
    - name: 单病种病例数
      format: '%.f例'
    - name: 单病种病例数_sort
      hide: true
    - name: 全部患者平均住院日
      format: '%.2f天'
    - name: 全部患者平均住院日_sort
      hide: true
    - name: 单病种平均住院日
      format: '%.2f天'
    - name: 单病种平均住院日_sort
      hide: true
    - name: 全部患者术前平均住院日
      format: '%.2f天'
    - name: 全部患者术前平均住院日_sort
      hide: true
    - name: 单病种术前平均住院日
      format: '%.2f天'
    - name: 单病种术前平均住院日_sort
      hide: true
    - name: 全部患者例均费用
      format: '%.2f元'
    - name: 全部患者例均费用_sort
      hide: true
    - name: 单病种例均费用
      format: '%.2f元'
    - name: 单病种例均费用_sort
      hide: true
    - name: 全部患者每日住院费用
      format: '%.2f元'
    - name: 全部患者每日住院费用_sort
      hide: true
    - name: 单病种每日住院费用
      format: '%.2f元'
    - name: 单病种每日住院费用_sort
      hide: true
    - name: 全部患者例均手术费
      format: '%.2f元'
    - name: 全部患者例均手术费_sort
      hide: true
    - name: 单病种例均手术费
      format: '%.2f元'
    - name: 单病种例均手术费_sort
      hide: true
    - name: 全部患者手术占比
      format: '%.2f%%'
    - name: 全部患者手术占比_sort
      hide: true
    - name: 单病种手术占比
      format: '%.2f%%'
    - name: 单病种手术占比_sort
      hide: true
    - name: 全部患者例均药品费用
      format: '%.2f元'
    - name: 全部患者例均药品费用_sort
      hide: true
    - name: 单病种例均药品费用
      format: '%.2f元'
    - name: 单病种例均药品费用_sort
      hide: true
    - name: 全部患者药品占比
      format: '%.2f%%'
    - name: 全部患者药品占比_sort
      hide: true
    - name: 单病种药品占比
      format: '%.2f%%'
    - name: 单病种药品占比_sort
      hide: true
    - name: 全部患者例均检查费用
      format: '%.2f元'
    - name: 全部患者例均检查费用_sort
      hide: true
    - name: 单病种例均检查费用
      format: '%.2f元'
    - name: 单病种例均检查费用_sort
      hide: true
    - name: 全部患者检查占比
      format: '%.2f%%'
    - name: 全部患者检查占比_sort
      hide: true
    - name: 单病种检查占比
      format: '%.2f%%'
    - name: 单病种检查占比_sort
      hide: true
    - name: 全部患者病死例数
      format: '%.f例'
    - name: 全部患者病死例数_sort
      hide: true
    - name: 单病种病死例数
      format: '%.f例'
    - name: 单病种病死例数_sort
      hide: true
    - name: 全部患者病死率
      format: '%.2f%%'
    - name: 全部患者病死率_sort
      hide: true
    - name: 单病种病死率
      format: '%.2f%%'
    - name: 单病种病死率_sort
      hide: true
    - name: 全部患者入院诊断符合病例数
      format: '%.f例'
    - name: 全部患者入院诊断符合病例数_sort
      hide: true
    - name: 单病种入院诊断符合病例数
      format: '%.f例'
    - name: 单病种入院诊断符合病例数_sort
      hide: true
    - name: 全部患者入院诊断符合率
      format: '%.2f%%'
    - name: 全部患者入院诊断符合率_sort
      hide: true
    - name: 单病种入院诊断符合率
      format: '%.2f%%'
    - name: 单病种入院诊断符合率_sort
      hide: true
    - name: 全部患者例均手术费
      format: '%.2f元'
    - name: 全部患者例均手术费_sort
      hide: true
    - name: 单病种例均手术费
      format: '%.2f元'
    - name: 单病种例均手术费_sort
      hide: true
    - name: 全部患者手术后诊断符合例数
      format: '%.f例'
    - name: 全部患者手术后诊断符合例数_sort
      hide: true
    - name: 单病种手术后诊断符合例数
      format: '%.f例'
    - name: 单病种手术后诊断符合例数_sort
      hide: true
    - name: 全部患者手术后诊断符合率
      format: '%.2f%%'
    - name: 全部患者手术后诊断符合率_sort
      hide: true
    - name: 单病种手术后诊断符合率
      format: '%.2f%%'
    - name: 单病种手术后诊断符合率_sort
      hide: true
    - name: 全部患者治愈例数
      format: '%.f例'
    - name: 全部患者治愈例数_sort
      hide: true
    - name: 单病种治愈例数
      format: '%.f例'
    - name: 单病种治愈例数_sort
      hide: true
    - name: 全部患者治愈率
      format: '%.2f%%'
    - name: 全部患者治愈率_sort
      hide: true
    - name: 单病种治愈率
      format: '%.2f%%'
    - name: 单病种治愈率_sort
      hide: true
    - name: 全部患者好转病例数
      format: '%.f例'
    - name: 全部患者好转病例数_sort
      hide: true
    - name: 单病种好转病例数
      format: '%.f例'
    - name: 单病种好转病例数_sort
      hide: true
    - name: 全部患者好转率
      format: '%.2f%%'
    - name: 全部患者好转率_sort
      hide: true
    - name: 单病种患者好转率
      format: '%.2f%%'
    - name: 单病种患者好转率_sort
      hide: true
    - name: 全部患者抗生素使用病例数
      format: '%.f例'
    - name: 全部患者抗生素使用病例数_sort
      hide: true
    - name: 单病种抗生素使用病例数
      format: '%.f例'
    - name: 单病种抗生素使用病例数_sort
      hide: true
    - name: 全部患者抗生素使用率
      format: '%.2f%%'
    - name: 全部患者抗生素使用率_sort
      hide: true
    - name: 单病种抗生素使用率
      format: '%.2f%%'
    - name: 单病种抗生素使用率_sort
      hide: true
    - name: 事中质控提醒数
      format: '%.f项'
    - name: 事中质控提醒数_sort
      hide: true
    - name: 事中质控完成数
      format: '%.f项'
    - name: 事中质控完成数_sort
      hide: true
    - name: 事中质控完成率
      format: '%.2f%%'
    - name: 事中质控完成率_sort
      hide: true
'''

# 单病种-质控统计-指标统计
SINGLE_DISEASE_QC_INDICATOR_YAML = '''
name: test
fields:
    - name: 病种名称
    - name: 单病种病例数
      format: '%.f例'
    - name: 单病种病例数_sort
      hide: true
    - name: 全部患者平均住院日
      hide: true
    - name: 全部患者平均住院日_sort
      hide: true
    - name: 单病种平均住院日
      format: '%.2f天'
    - name: 单病种平均住院日_sort
      hide: true
    - name: 全部患者术前平均住院日
      hide: true
    - name: 全部患者术前平均住院日_sort
      hide: true
    - name: 单病种术前平均住院日
      format: '%.2f天'
    - name: 单病种术前平均住院日_sort
      hide: true
    - name: 全部患者例均费用
      hide: true
    - name: 全部患者例均费用_sort
      hide: true
    - name: 单病种例均费用
      format: '%.2f元'
    - name: 单病种例均费用_sort
      hide: true
    - name: 全部患者每日住院费用
      hide: true
    - name: 全部患者每日住院费用_sort
      hide: true
    - name: 单病种每日住院费用
      format: '%.2f元'
    - name: 单病种每日住院费用_sort
      hide: true
    - name: 全部患者例均手术费
      hide: true
    - name: 全部患者例均手术费_sort
      hide: true
    - name: 单病种例均手术费
      format: '%.2f元'
    - name: 单病种例均手术费_sort
      hide: true
    - name: 全部患者手术占比
      hide: true
    - name: 全部患者手术占比_sort
      hide: true
    - name: 单病种手术占比
      format: '%.2f%%'
    - name: 单病种手术占比_sort
      hide: true
    - name: 全部患者例均药品费用
      hide: true
    - name: 全部患者例均药品费用_sort
      hide: true
    - name: 单病种例均药品费用
      format: '%.2f元'
    - name: 单病种例均药品费用_sort
      hide: true
    - name: 全部患者药品占比
      hide: true
    - name: 全部患者药品占比_sort
      hide: true
    - name: 单病种药品占比
      format: '%.2f%%'
    - name: 单病种药品占比_sort
      hide: true
    - name: 全部患者例均检查费用
      hide: true
    - name: 全部患者例均检查费用_sort
      hide: true
    - name: 单病种例均检查费用
      format: '%.2f元'
    - name: 单病种例均检查费用_sort
      hide: true
    - name: 全部患者检查占比
      hide: true
    - name: 全部患者检查占比_sort
      hide: true
    - name: 单病种检查占比
      format: '%.2f%%'
    - name: 单病种检查占比_sort
      hide: true
    - name: 全部患者病死例数
      hide: true
    - name: 全部患者病死例数_sort
      hide: true
    - name: 单病种病死例数
      format: '%.f例'
    - name: 单病种病死例数_sort
      hide: true
    - name: 全部患者病死率
      hide: true
    - name: 全部患者病死率_sort
      hide: true
    - name: 单病种病死率
      format: '%.2f%%'
    - name: 单病种病死率_sort
      hide: true
    - name: 全部患者入院诊断符合病例数
      hide: true
    - name: 全部患者入院诊断符合病例数_sort
      hide: true
    - name: 单病种入院诊断符合病例数
      format: '%.f例'
    - name: 单病种入院诊断符合病例数_sort
      hide: true
    - name: 全部患者入院诊断符合率
      hide: true
    - name: 全部患者入院诊断符合率_sort
      hide: true
    - name: 单病种入院诊断符合率
      format: '%.2f%%'
    - name: 单病种入院诊断符合率_sort
      hide: true
    - name: 全部患者手术病例
      hide: true
    - name: 全部患者手术病例_sort
      hide: true
    - name: 单病种手术病例
      format: '%.f例'
    - name: 单病种手术病例_sort
      hide: true
    - name: 全部患者手术后诊断符合例数
      hide: true
    - name: 全部患者手术后诊断符合例数_sort
      hide: true
    - name: 单病种手术后诊断符合例数
      format: '%.f例'
    - name: 单病种手术后诊断符合例数_sort
      hide: true
    - name: 全部患者手术后诊断符合率
      hide: true
    - name: 全部患者手术后诊断符合率_sort
      hide: true
    - name: 单病种手术后诊断符合率
      format: '%.2f%%'
    - name: 单病种手术后诊断符合率_sort
      hide: true
    - name: 全部患者治愈例数
      hide: true
    - name: 全部患者治愈例数_sort
      hide: true
    - name: 单病种治愈例数
      format: '%.f例'
    - name: 单病种治愈例数_sort
      hide: true
    - name: 全部患者治愈率
      hide: true
    - name: 全部患者治愈率_sort
      hide: true
    - name: 单病种治愈率
      format: '%.2f%%'
    - name: 单病种治愈率_sort
      hide: true
    - name: 全部患者好转病例数
      hide: true
    - name: 全部患者好转病例数_sort
      hide: true
    - name: 单病种好转病例数
      format: '%.f例'
    - name: 单病种好转病例数_sort
      hide: true
    - name: 全部患者好转率
      hide: true
    - name: 全部患者好转率_sort
      hide: true
    - name: 单病种患者好转率
      format: '%.2f%%'
    - name: 单病种患者好转率_sort
      hide: true
    - name: 全部患者抗生素使用病例数
      hide: true
    - name: 全部患者抗生素使用病例数_sort
      hide: true
    - name: 单病种抗生素使用病例数
      format: '%.f例'
    - name: 单病种抗生素使用病例数_sort
      hide: true
    - name: 全部患者抗生素使用率
      hide: true
    - name: 全部患者抗生素使用率_sort
      hide: true
    - name: 单病种抗生素使用率
      format: '%.2f%%'
    - name: 单病种抗生素使用率_sort
      hide: true
    - name: 事中质控提醒数
      format: '%.f项'
    - name: 事中质控提醒数_sort
      hide: true
    - name: 事中质控完成数
      format: '%.f项'
    - name: 事中质控完成数_sort
      hide: true
    - name: 事中质控完成率
      format: '%.2f%%'
    - name: 事中质控完成率_sort
      hide: true
groupFields:
    - name: 病种缩写
'''

# 单病种-质控统计-指标详情-表1
SINGLE_DISEASE_QC_INDICATOR_TABLE_1 = '''
name: test
fields:
    - name: 病种简称
    - name: 病种名称
    - name: 单病种病例
    - name: 上报成功
    - name: 应上报实上报率
groupFields:
    - name: 病种分类
'''

# 单病种-质控统计-指标详情-表2
SINGLE_DISEASE_QC_INDICATOR_TABLE_2 = '''
name: test
fields:
    - name: 就诊号
    - name: 科室
    - name: 患者
    - name: 离院时间
    - name: 病种分类
    - name: patientId
    - name: disease_id
groupFields:
    - name: 就诊类型
'''

# 单病种指标使用表1指标
SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_1 = ['覆盖病种数']

# 单病种指标使用表2指标
SINGLE_DISEASE_QC_INDICATOR_USE_TABLE_2 = ['病例数', '例均住院日', '术前平均住院日', '例均费用', '每日住院费用', '例均手术费', '手术占比', '例均药品费用', '药品占比', '例均检查费用', '检查占比', '病死例数', '病死率', '入院诊断符合病例数', '入院诊断符合率', '手术病例', '手术后诊断符合率', '好转病例数', '抗生素使用病例数', '抗生素使用率', '事中质控提醒数', '事中质控完成数', '事中质控完成率']

# 单病种-质控统计-科室分析
SINGLE_DISEASE_QC_DEPARTMENT_YAML = '''
name: test
fields:
    - name: 科室名称
    {}
groupFields:
    - name: 科室编码
'''.format(SINGLE_DISEASE_QC_SAME_YAML)

# 单病种-质控分析-医生分析
SINGLE_DISEASE_QC_DOCTOR_YAML = '''
name: test
fields:
    - name: 医生姓名
    - name: 科室编码
    - name: 科室名称
    {}
groupFields:
    - name: 医生编码
'''.format(SINGLE_DISEASE_QC_SAME_YAML)

# 单病种-上报分析-上报率统计
SINGLE_DISEASE_ANALYSE_RATE_YAML = '''
name: test
fields:
    - name: 就诊号
    - name: 科室
    - name: 患者
    - name: 离院时间
    - name: 病种分类
    - name: 状态
    - name: 提交人
    - name: 审核人
groupFields:
    - name: 就诊类型
'''

# 全院(科室/病区)病案指标-病历书写时效性、诊疗行为符合率等-查询
BRANCH_TIMELINESS_RATE_YAML = '''
name: test
fields:
    - name: 入院记录24小时内完成率
      hide: ce.inrecord24hcomplete, cmt.inrecord24hcomplete_time
    - name: 手术记录24小时内完成率
      hide: ce.opsrecord24hcomplete, cmt.opsrecord24hcomplete_time
    - name: 出院记录24小时内完成率
      hide: ce.outrecord24hcomplete, cmt.outrecord24hcomplete_time
    - name: 病案首页24小时内完成率
      hide: ce.firstpage24hcomplete, cmt.firstpage24hcomplete_time
    - name: 抗菌药物使用记录符合率
      hide: true
    - name: 手术相关记录完整率
      hide: ce.opsrecordwhole
    - name: 植入物相关记录符合率
      hide: cmt.implantmeet
    - name: 临床用血相关记录符合率
      hide: cmt.clinicalbloodmeet
    - name: 医师查房记录完整率
      hide: ce.doctorroundswhole
    - name: 患者抢救记录及时完成率
      hide: ce.rescuerecord6hcomplete
    - name: 出院患者病历2日归档率
      hide: ce.applyrn - ce.dischargern
    - name: 出院患者病历归档完整率
      hide: ce.medicalrecordwhole
    - name: 主要诊断填写正确率
      hide: ce.isprimarydiagvalid
    - name: 主要诊断编码正确率
      hide: ce.isminordiagvalid
    - name: 主要手术填写正确率
      hide: ce.isprimaryopervalid
    - name: 主要手术编码正确率
      hide: ce.isminoropervalid
    - name: 不合理复制病历发生率
      hide: ce.isemrcopy
    - name: 知情同意书规范签署率
      hide: ce.isnormmrc
    - name: 甲级病历率
      hide: ce.ismajor
groupFields:
    - name: {branch}
'''

# 医生病案指标-病历书写时效性、诊疗行为符合率等-查询
DOCTOR_TIMELINESS_RATE_YAML = '''
name: test
fields:
    - name: 责任医生
    - name: 入院记录24小时内完成率
      hide: ce.inrecord24hcomplete, cmt.inrecord24hcomplete_time
    - name: 手术记录24小时内完成率
      hide: ce.opsrecord24hcomplete, cmt.opsrecord24hcomplete_time
    - name: 出院记录24小时内完成率
      hide: ce.outrecord24hcomplete, cmt.outrecord24hcomplete_time
    - name: 病案首页24小时内完成率
      hide: ce.firstpage24hcomplete, cmt.firstpage24hcomplete_time
    - name: 抗菌药物使用记录符合率
      hide: true
    - name: 手术相关记录完整率
      hide: ce.opsrecordwhole
    - name: 植入物相关记录符合率
      hide: cmt.implantmeet
    - name: 临床用血相关记录符合率
      hide: cmt.clinicalbloodmeet
    - name: 医师查房记录完整率
      hide: ce.doctorroundswhole
    - name: 患者抢救记录及时完成率
      hide: ce.rescuerecord6hcomplete
    - name: 出院患者病历2日归档率
      hide: ce.applyrn - ce.dischargern
    - name: 出院患者病历归档完整率
      hide: ce.medicalrecordwhole
    - name: 主要诊断填写正确率
      hide: ce.isprimarydiagvalid
    - name: 主要诊断编码正确率
      hide: ce.isminordiagvalid
    - name: 主要手术填写正确率
      hide: ce.isprimaryopervalid
    - name: 主要手术编码正确率
      hide: ce.isminoropervalid
    - name: 不合理复制病历发生率
      hide: ce.isemrcopy
    - name: 知情同意书规范签署率
      hide: ce.isnormmrc
    - name: 甲级病历率
      hide: ce.ismajor
groupFields:
    - name: 科室
'''



# 全院病案指标-指标明细列表
BRANCH_TIMELINESS_DETAIL_LIST_YAML = '''
name: test
fields:
    - name: 姓名
    - name: 科室
    - name: 病区
    - name: 入院日期
    - name: 出院日期
    - name: 责任医生
    - name: 病历状态
    - name: 指标符合状态
groupFields:
    - name: 病历号
'''

# 全院病案指标-指标明细列表-时效性相关指标
BRANCH_TIMELINESS_DETAIL_TIME_LIST_YAML = '''
name: test
fields:
    - name: 姓名
    - name: 科室
    - name: 病区
    - name: 入院日期
    - name: 出院日期
    - name: 责任医生
    - name: 病历状态
    - name: 指标符合状态
    - name: 指标完成时效
groupFields:
    - name: 病历号
'''

# 工作量统计报表
WORKLOAD_REPORT_YAML = '''
name: workload
fields:
    - name: 出院人数
    - name: 提交质控病案数
    - name: 科室质控病案数
    - name: 科室质控病案比例
      format: '%.2f%%'
    - name: 院级质控病案数
    - name: 院级质控病案比例
      format: '%.2f%%'
    - name: 首页质控病案数
    - name: 首页质控病案比例
      format: '%.2f%%'
    - name: 总质控数量
    - name: 总体病案质控比例
      format: '%.2f%%'
    - name: 甲级病案数
    - name: 乙级病案数
    - name: 丙级病案数
    - name: 甲级率
      format: '%.2f%%'
    - name: 输血患者人数
    - name: 科室输血病案质控人数
    - name: 科室输血病案质控比例
      format: '%.2f%%'
    - name: 院级输血病案质控数
    - name: 院级输血病案质控比例
      format: '%.2f%%'
    - name: 死亡患者人数
    - name: 科室死亡病案质控数
    - name: 科室死亡病案质控比例
      format: '%.2f%%'
    - name: 院级死亡病案质控数
    - name: 院级死亡病案质控比例
      format: '%.2f%%'
    - name: 超30天患者人数
    - name: 科室超30天病案质控数
    - name: 科室超30天病案质控比例
      format: '%.2f%%'
    - name: 院级超30天病案质控数
    - name: 院级超30天病案质控比例
      format: '%.2f%%'
groupFields:
    - name: 科室
'''

# 单病种-指标详情-无表格指标
SINGLE_DISEASE_NOTABLE_FIELD = ['例均住院日', '例均费用', '每日住院费用', '例均手术费', '例均药品费用', '例均检查费用', '事中质控提醒数', '事中质控完成数']

# 单病种不排序字段数组
SINGLE_DISEASE_NO_SORT_FIELD = ["病种名称", "病种简称", "科室编码", "科室名称", "医生编码", "医生姓名", "病种缩写", "审核员名称", "审核员编码", "所在科室名称",
                                "所在科室编码"]

# 单病种明细列表
SINGLE_DISEASE_FIELD_LIST = ['单病种病例', '应上报实上报率', '已取消病例', '待提交病例', '待审核病例', '待上报病例', '上报失败病例', '上报成功病例', '上报成功率', '例均填表耗时（单位：天）', '例均出院-上报耗时（单位：天）', '按时提交病例', '延时提交病例', '按时提交率', '延时提交率', '按时审核病例', '延时审核病例', '按时审核率', '延时审核率', '按时上报病例', '延时上报病例', '按时上报率', '延时上报率', '机器获取数据项', '机器填报率', '人工填报数据项', '人工填表率']

# 单病种质控明细列表
SINGLE_DISEASE_QC_FIELD_LIST = ['覆盖病种数', '全部患者病例数','单病种病例数', '全部患者平均住院日', '单病种平均住院日', '全部患者术前平均住院日', '单病种术前平均住院日', '全部患者例均费用', '单病种例均费用', '全部患者每日住院费用', '单病种每日住院费用', '全部患者例均手术费', '单病种例均手术费', '全部患者手术占比', '单病种手术占比', '全部患者例均药品费用', '单病种例均药品费用', '全部患者药品占比', '单病种药品占比', '全部患者例均检查费用', '单病种例均检查费用', '全部患者检查占比', '单病种检查占比', '全部患者病死例数', '单病种病死例数', '全部患者病死率', '单病种病死率', '全部患者入院诊断符合病例数', '单病种入院诊断符合病例数', '全部患者入院诊断符合率', '单病种入院诊断符合率','全部患者手术病例', '单病种手术病例', '全部患者手术后诊断符合例数', '单病种手术后诊断符合例数', '全部患者手术后诊断符合率', '单病种手术后诊断符合率', '全部患者治愈例数', '单病种治愈例数', '全部患者治愈率', '单病种治愈率', '全部患者好转病例数', '单病种好转病例数', '全部患者好转率', '单病种患者好转率', '全部患者抗生素使用病例数', '单病种抗生素使用病例数', '全部患者抗生素使用率', '单病种抗生素使用率', '事中质控提醒数', '事中质控完成数', '事中质控完成率']

# 单病种质控-指标质控统计
SINGLE_DISEASE_QC_INDICATOR_FIELD_LIST = ['单病种病例数', '全部患者平均住院日', '单病种平均住院日', '全部患者术前平均住院日', '单病种术前平均住院日', '全部患者例均费用', '单病种例均费用', '全部患者每日住院费用', '单病种每日住院费用', '全部患者例均手术费', '单病种例均手术费', '全部患者手术占比', '单病种手术占比', '全部患者例均药品费用', '单病种例均药品费用', '全部患者药品占比', '单病种药品占比', '全部患者例均检查费用', '单病种例均检查费用', '全部患者检查占比', '单病种检查占比', '全部患者病死例数', '单病种病死例数', '全部患者病死率', '单病种病死率', '全部患者入院诊断符合病例数', '单病种入院诊断符合病例数', '全部患者入院诊断符合率', '单病种入院诊断符合率','全部患者手术病例', '单病种手术病例', '全部患者手术后诊断符合例数', '单病种手术后诊断符合例数', '全部患者手术后诊断符合率', '单病种手术后诊断符合率', '全部患者治愈例数', '单病种治愈例数', '全部患者治愈率', '单病种治愈率', '全部患者好转病例数', '单病种好转病例数', '全部患者好转率', '单病种患者好转率', '全部患者抗生素使用病例数', '单病种抗生素使用病例数', '全部患者抗生素使用率', '单病种抗生素使用率', '事中质控提醒数', '事中质控完成数', '事中质控完成率']
# 质控列表导出明细基础结构
QC_LIST_EXPORT_DATA = {"重点病历": "", "问题数": "", "分数": "", "姓名": "", "科室": "", "病区": "", "入院日期": "", "出院日期": "",
                       "住院天数": "", "责任医生": "", "分配医生": "", "质控医生": "", "质控日期": "", "签收日期": "", "状态": "", "问题描述": "",
                       "病案扣分": "", "首页扣分": "", "审核人": "", "审核日期": "", "dischargeTime": "", "admitTime": "", "auditTime": "",
                       "receiveTime": ""}

# 排序字段映射字典
QC_LIST_SORT_DICT = {"dischargeTime": "出院日期", "admitTime": "入院日期", "auditTime": "质控日期", "receiveTime": "签收日期"}
SORT_DESC_DICT = {"DESC": -1, "ASC": 1}

# 全院病案指标-病历书写时效性、诊疗行为符合率等指标对应一级名称字典
BRANCH_TIMELINESS_RATE_TARGET_FIRST_NAME_DICT = {"入院记录24小时内完成率": "病历书写时效性指标", "手术记录24小时内完成率": "病历书写时效性指标",
                                                 "出院记录24小时内完成率": "病历书写时效性指标", "手术相关记录完整率": "诊疗行为符合率",
                                                 "医师查房记录完整率": "诊疗行为符合率", "出院患者病历2日归档率": "病历归档质量指标",
                                                 "出院患者病历归档完整率": "病历归档质量指标", "甲级病历率": "病历归档质量指标",
                                                 "病案首页24小时内完成率": "病历书写时效性指标", "抗菌药物使用记录符合率": "诊疗行为符合率",
                                                 "植入物相关记录符合率": "诊疗行为符合率", "临床用血相关记录符合率": "诊疗行为符合率",
                                                 "患者抢救记录及时完成率": "诊疗行为符合率", "主要诊断填写正确率": "病历归档质量指标",
                                                 "主要诊断编码正确率": "病历归档质量指标", "主要手术填写正确率": "病历归档质量指标",
                                                 "主要手术编码正确率": "病历归档质量指标", "不合格复制病历发生率": "病历归档质量指标",
                                                 "知情同意书规范签署率": "病历归档质量指标", "不合理复制病历发生率": "病历归档质量指标"}

# 全院病案指标-指标明细对应数据库字段字典
BRANCH_TARGET_SQL_FIELD_DICT = {"入院记录24小时内完成率": "ce.inrecord24hcomplete, cmt.inrecord24hcomplete_time", "手术记录24小时内完成率": "ce.opsrecord24hcomplete, cmt.opsrecord24hcomplete_time",
                                "出院记录24小时内完成率": "ce.outrecord24hcomplete, cmt.outrecord24hcomplete_time", "手术相关记录完整率": "ce.opsrecordwhole",
                                "医师查房记录完整率": "ce.doctorroundswhole", "出院患者病历2日归档率": "ce.applyrn - ce.dischargern",
                                "出院患者病历归档完整率": "ce.medicalrecordwhole", "甲级病历率": "ce.ismajor",
                                "病案首页24小时内完成率": "ce.firstpage24hcomplete, cmt.firstpage24hcomplete_time", "临床用血相关记录符合率": "cmt.clinicalbloodmeet",
                                "主要诊断填写正确率": "ce.isprimarydiagvalid", "主要诊断编码正确率": "ce.isminordiagvalid",
                                "主要手术填写正确率": "ce.isprimaryopervalid", "主要手术编码正确率": "ce.isminoropervalid",
                                "患者抢救记录及时完成率": "ce.rescuerecord6hcomplete", "不合理复制病历发生率": "ce.isemrcopy",
                                "知情同意书规范签署率": "ce.isnormmrc", "植入物相关记录符合率": "cmt.implantmeet"}


# 全院病案指标-指标明细对应数据库条件字典
BRANCH_TARGET_FIELD_DICT = {
    "入院记录24小时内完成率": "ce.inrecord24hcomplete = '{res}' and ce.isinrecord= '是' ",
    "手术记录24小时内完成率": "ce.opsrecord24hcomplete = '{res}' and ce.isopstendrecord= '是' ",
    "出院记录24小时内完成率": "ce.outrecord24hcomplete = '{res}' and ce.isoutrecord='是' ",
    "手术相关记录完整率": "ce.opsrecordwhole = '{res}' and ce.isopstendrecord='是' ",
    "医师查房记录完整率": "ce.doctorroundswhole = '{res}' ",
    "出院患者病历2日归档率": "ce.applyrn - ce.dischargern {compare} 2 ",
    "出院患者病历归档完整率": "ce.medicalrecordwhole = '{res}' ",
    "甲级病历率": "ce.ismajor = '{res}' ",
    "病案首页24小时内完成率": "ce.firstpage24hcomplete = '{res}'",
    "临床用血相关记录符合率": "cmt.clinicalbloodmeet = '{res}' and cmt.isclinicalblood = '是'",
    "患者抢救记录及时完成率": "ce.rescuerecord6hcomplete = '{res}' and ce.isrescuerecord = '是'",
    "主要诊断填写正确率": "ce.isprimarydiagvalid = '{res}'",
    "主要诊断编码正确率": "ce.isminordiagvalid = '{res}'",
    "主要手术填写正确率": "ce.isprimaryopervalid = '{res}'",
    "主要手术编码正确率": "ce.isminoropervalid = '{res}'",
    "植入物相关记录符合率": "cmt.implantmeet = '{res}' and cmt.isopstendrecord = '是'",
    "不合理复制病历发生率": "ce.isemrcopy = '{res}'",
    "知情同意书规范签署率": "ce.isnormmrc = '{res}' and ce.ismrc = '是'",
}

# 全院病案指标-指标明细对应数据库字段字典
BRANCH_TARGET_QUERY_FIELD_DICT = {
    "入院记录24小时内完成率": ("sum(case when a.inrecord24hcomplete='是' and a.isinrecord='是' then 1 else 0 end)", "sum(case when  a.isinrecord='是' then 1 else 0 end)"),
    "手术记录24小时内完成率": ("sum(case when a.opsrecord24hcomplete='是' and a.isopstendrecord='是' then 1 else 0 end)", "sum(case when a.isopstendrecord='是' then 1 else 0 end)"),
    "出院记录24小时内完成率": ("sum(case when a.outrecord24hcomplete='是' and a.isoutrecord='是'  then 1 else 0 end)", "sum(case when a.isoutrecord='是'  then 1 else 0 end)"),
    "手术相关记录完整率": ("sum(case when a.opsrecordwhole='是' and a.isopstendrecord='是' then 1 else 0 end)", "sum(case when a.isopstendrecord='是' then 1 else 0 end)"),
    "医师查房记录完整率": ("sum(case when a.doctorroundswhole='是' then 1 else 0 end)", "sum(1)"),
    "出院患者病历2日归档率": ("sum(case when a.applyrn - a.dischargern <= 2 then 1 else 0 end)", "sum(1)"),
    "出院患者病历归档完整率": ("sum(case when a.medicalrecordwhole='是' then 1 else 0 end)", "sum(1)"),
    "甲级病历率": ("sum(case when a.ismajor='是' then 1 else 0 end)", "sum(1)")
}

# 质控分析-缺陷率统计-科室-导出标题
DEFECT_RATE_TITLE_DEPT = ["科室", "诊疗组", "责任医生", "已提交病历数", "首次提交不合格病历数", "首次提交病历缺陷率"]

# 质控分析-缺陷率统计-科室-导出标题[无诊疗组]
DEFECT_RATE_TITLE_DEPT_NO_GROUP = ["科室", "责任医生", "已提交病历数", "首次提交不合格病历数", "首次提交病历缺陷率"]

# 质控分析-缺陷率统计-病区-导出标题
DEFECT_RATE_TITLE_WARD = ["病区", "责任医生", "已提交病历数", "首次提交不合格病历数", "首次提交病历缺陷率"]

# 质控分析-缺陷率统计明细-科室-导出标题
DEFECT_RATE_DETAIL_TITLE_DEPT = ["病历号", "姓名", "入院日期", "出院日期", "科室", "诊疗组", "责任医生", "首次提交病历分数", "首次提交是否为合格病历", "病历状态"]

# 质控分析-缺陷率统计明细-科室-导出标题[无诊疗组]
DEFECT_RATE_DETAIL_TITLE_DEPT_NO_GROUP = ["病历号", "姓名", "入院日期", "出院日期", "科室", "责任医生", "首次提交病历分数", "首次提交是否为合格病历", "病历状态"]

# 质控分析-缺陷率统计明细-病区-导出标题
DEFECT_RATE_DETAIL_TITLE_WARD = ["病历号", "姓名", "入院日期", "出院日期", "病区", "责任医生", "首次提交病历分数", "首次提交是否为合格病历", "病历状态"]

# 编码病历列表导出配置
CASE_LIST_YAML = '''
name: test
fields:
    - name: 问题
    - name: 分数
    - name: 病历号
    - name: 姓名
    - name: 科室
    - name: 病区
    - name: 入院日期
    - name: 出院日期
    - name: 住院天数
    - name: 责任医生
    - name: 编码员
    - name: 编码日期
    - name: 编码状态
    - name: dischargeTime
      hide: true
groupFields:
    - name: 重点病历
'''
