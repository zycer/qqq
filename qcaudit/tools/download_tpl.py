#!/usr/bin/env python3
from argparse import ArgumentParser
import streamlit as st
import pandas as pd
from . import QCDataBaseManager


def getParser():
    # prog: 的内容是页面左侧"功能清单选择"下拉框中显示的内容
    # description: 功能说明, 可以写markdown, 会出现右侧顶部
    parser = ArgumentParser(prog='下载模板', description='''
    **模板下载**
    - 质控点设置模板
    - 配置项设置模板，数据库地址必要
    ''')
    # 模板功能选项下拉列表
    parser.add_argument('--output-tpl', dest='output_tpl', help='选择下载模板',
                        choices=['质控点设置', '规则组设置', '配置项设置', '用户科室设置'], default='质控点设置')
    # 文件名
    parser.add_argument('-fn', dest='filename', help='自定义模板下载文件名')
    # 数据库连接
    parser.add_argument('--db-url', dest='dbUrl', help='数据库url, Default:%(default)s',
                        default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default/qcmanager?charset=utf8mb4')

    return parser


def process(args):
    if args.output_tpl == '质控点设置':
        filename = f'{args.filename or "质控点导入模板"}.csv'

        # titles = ['质控点编号', '报警文书', '质控点名称', '报警提示信息', '质控点规则', '类别', '分数', '是否强控', '是否开启']
        data = [{
            '质控点编号': 'SY001',
            '报警文书': '病案首页',
            '质控点名称': '参考：病案首页入院时间错误',
            '报警提示信息': '参考：病案首页入院时间XXX错误',
            '质控点规则': '参考：病案首页入院时间和入院记录入院时间不一致则报警',
            '类别': '枚举 时效性，一致性，正确性，完整性',
            '分数': '2分',
            '是否强控': '是 或者 否 或者 空，空表示否',
            '是否开启': '是 或者 否 或者 空，空表示否'
        }]
        data = pd.DataFrame(data).to_csv().encode('utf-8')

        st.download_button('模板下载', data=data, file_name=filename, help='点击下载质控点导入模板')

        return "质控点设置模板，版本日期：2022-02-08"

    elif args.output_tpl == '配置项设置':
        filename = f'{args.filename or "配置项导入模板"}.csv'

        # 从数据库中读取配置项列表，导出成文件
        db = QCDataBaseManager(args.dbUrl)
        data = []
        cache = []
        with db.session() as session:
            for item in session.query(db.models['configItem']).all():
                data.append({'配置项': item.name, '配置值': item.value, '配置项用法备注': config_dict.get(item.name, '')})
                cache.append(item.name)
        for k, v in config_dict.items():
            if k in cache:
                continue
            data.append({'配置项': k, '配置值': '', '配置项用法备注': v})
        data = pd.DataFrame(data).to_csv().encode('utf-8')

        st.download_button('模板下载', data=data, file_name=filename, help='点击下载配置项设置模板')

        return "配置项设置模板，版本日期：2022-02-08"

    elif args.output_tpl == '规则组设置':
        filename = f'{args.filename or "规则组导入模板"}.csv'

        # titles = ['规则组', '规则组分类', '质控点编号', '每处扣分', '最高分']
        data = [{
            '规则组': '枚举：科室质控，病案质控，编码质控，专家质控，事中质控',
            '规则组分类': '要求：自定义分类 或 空，不存在的分类自动创建',
            '质控点编号': 'SY001',
            '每处扣分': '格式：2分/处，2分，2，每处2分',
            '最高分': '格式：包含数字的字符串，10分',
        }]
        data = pd.DataFrame(data).to_csv().encode('utf-8')

        st.download_button('模板下载', data=data, file_name=filename, help='点击下载规则组设置模板')

        return '''规则组设置模板，版本日期：2022-02-08  
        规则组 枚举（"病案质控"，"科室质控"，"编码质控"，"专家质控"，"事中质控"）  
        规则组分类，如果没有分类的话，归为默认的分类，如果分类不存在，创建新分类
        '''

    elif args.output_tpl == '用户科室设置':
        filename = f'{args.filename or "用户科室导入模板"}.csv'

        data = [{
            '编号': '',
            '科室': '',
        }]
        data = pd.DataFrame(data).to_csv().encode('utf-8')

        st.download_button('模板下载', data=data, file_name=filename, help='点击下载用户科室导入模板')

        return '''用户科室设置模板，版本日期：2022-05-31  
        创建用户时科室选择项导入
        '''

    return '模板下载'


# ArgumentParser对象, 必须有此变量
STREAMLIT_PARSER = getParser()
# 处理参数的函数, 必须有此变量
STREAMLIT_FUNCTION = process

# 配置项字典
config_dict = {
    'qc.department': '是否需要科室质控节点',
    'qc.hospital': '是否需要质控节点',
    'qc.firstpage': '是否需要质控节点',
    'qc.expert': '是否需要质控节点',
    'qc.menu.enabled': '菜单',
    'qc.group.active.active': 'qcetl',
    'qc.group.department.active': 'qcetl',
    'qc.group.expert.active': 'qcetl',
    'qc.group.hospital.active': 'qcetl',
    'qc.group.firstpage.active': 'qcetl',
    'qc.group.hospital.archive': 'qcetl',
    'qc.group.firstpage.archive': 'qcetl',
    'qc.group.expert.archive': 'qcetl',
    'qc.group.department.archive': 'qcetl',
    'qc.autoarchive.enabled': '开启自动归档',
    'qc.doctor.case.display.rule': '待申请病历显示规则',
    'qc.doctor.score.display': '是否显示分数和等级',
    'qc.doctor.extract.display': '是否需要显示抽检病历',
    'qc.doctor.attendDoctor.display': '医生姓名是否显示',
    'qc.doctor.tabs': '页签显示哪几个',
    'qc.doctor.veto': '低于90分病历是否可提交',
    'wardFlag': '显示【楼层】还是【病区】',
    'attendingFlag': '所有Attending、attending、ATTENDING',
    'safeKeepingFlag': '是否需要封存功能',
    'qc.patientId.name': '病历号/住院号/病案号',
    'qc.stats.dimension': '按科室统计还是按病区统计',
    'qc.archived.step': '哪个节点审核通过算归档',
    'qc.archived.problem.display': '归档后问题是否显示',
    'doctorFRFlag': '【F/R勾选】查询条件和列表一起配置',
    'qc.user.password.complexity': '是否使用安全密码',
    'qc.branch.display': '是否分院区',
    'qc.emrstatus.display': '审核页面-中间文书的未保存、已保存、已审核状态，是否需要显示',
    'qc.detail.monopathy': '是否需要单病种质控功能',
    'qc.detail.problemlist': '是否需要病历质控问题列表功能',
    'qc.detail.revoke.refuse': '是否需要撤销驳回功能',
    'qc.emr.sort': '审核页面：中间文书排序配置',
    'qc.assign.dimension': '查看抽取历史：分配按钮是用病区分配还是用科室分配',
    'qc.department.score.flag': '是否显示分数和等级',
    'qc.department.case.scope.archived': '科室需要质控的病历范围',
    'qc.department.extract': '是否需要科室抽取功能',
    'qc.department.extract.auto.assign': '是否需要科室自动分配功能',
    'qc.department.case.notapply.audit': '已出院未申请状态是否需要质控',
    'qc.department.final': '是否需要科室审核功能',
    'qc.department.finish.notify.doctor': '完成质控或审核通过时，是否需要通知医生',
    'qc.department.private': '是否仅限质控本科病历',
    'qc.department.precondition': '科室质控前置环节',
    'qc.department.addReturn': '是否需要追加退回按钮',
    'qc.hospital.score.flag': '是否显示分数和等级',
    'qc.hospital.case.scope.archived': '需要质控的病历范围',
    'qc.hospital.extract': '是否需要抽取功能',
    'qc.hospital.extract.auto.assign': '是否需要自动分配功能',
    'qc.hospital.case.notapply.audit': '已出院未申请状态是否需要质控',
    'qc.hospital.finish.notify.doctor': '完成质控或审核通过时，是否需要通知医生',
    'qc.hospital.final': '是否需要审核功能',
    'qc.hospital.precondition': '病案质控前置环节',
    'qc.hospital.addReturn': '是否需要追加退回按钮',
    'qc.firstpage.score.flag': '是否显示分数和等级',
    'qc.firstpage.case.scope.archived': '需要质控的病历范围',
    'qc.firstpage.extract': '是否需要抽取功能',
    'qc.firstpage.extract.auto.assign': '是否需要自动分配功能',
    'qc.firstpage.final': '是否需要审核功能',
    'qc.firstpage.case.notapply.audit': '已出院未申请状态是否需要质控',
    'qc.firstpage.medcare': '是否需要医保结算清单',
    'qc.firstpage.drgs': '是否需要DGRs分组功能',
    'qc.firstpage.finish.notify.doctor': '完成质控或审核通过时，是否需要通知医生',
    'qc.firstpage.precondition': '编码质控前置环节',
    'qc.firstpage.addReturn': '是否需要追加退回按钮',
    'qc.expert.score.flag': '是否显示分数和等级',
    'qc.expert.case.scope.archived': '需要质控的病历范围',
    'qc.expert.extract': '是否需要抽取功能',
    'qc.expert.case.notapply.audit': '已出院未申请状态是否需要质控',
    'qc.expert.extract.auto.assign': '是否需要自动分配功能',
    'qc.expert.finish.notify.doctor': '完成质控或审核通过时，是否需要通知医生',
    'qc.expert.final': '是否需要审核功能',
    'qc.expert.precondition': '专家质控前置环节',
    'qc.expert.addReturn': '是否需要追加退回按钮',
}
