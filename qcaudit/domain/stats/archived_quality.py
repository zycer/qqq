from collections import namedtuple

import xlsxwriter
from sqlalchemy import Column, Integer, String, Date, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CaseArchiveExtend(Base):
    __tablename__ = 'case_archive_extend'

    caseid = Column(String(100), primary_key=True)
    name = Column(String(100))
    admittime = Column(Date)
    outdeptname = Column(String(100))
    outdeptid = Column(String(50))
    wardid = Column(String(100))
    wardname = Column(String(100))
    attendDoctor = Column(String(100))
    status = Column(Integer)
    dischargetime = Column(Date)
    branch = Column(String(100))
    medicalgroupname = Column(String(255))
    score = Column(Float)
    is_mq = Column(String(10))
    caselevel = Column(String(10))


class ArchivedQualityStats:

    def __init__(self, type_, branch, department, group, ward, attend, startTime, endTime):
        self.type_ = type_
        self.branch = branch or '全部'
        self.dept = department or '全部'
        self.group = group or '全部'
        self.ward = ward or '全部'
        self.attend = attend or '全部'
        self.begindate = startTime
        self.enddate = endTime

    def stats(self, session, group_flag=False):

        ItemData = namedtuple('ArchQuality', ['dept', 'group', 'attend', 'ward', 'data'])

        proc_name = f"归档病历质量统计{self.type_}"
        proc_dept = self.dept if self.type_ == "科室" else self.ward
        args = (proc_name, proc_dept, self.group, self.attend, self.branch, self.begindate, self.enddate)

        call_sql = f"call pr_case_archivecase('%s', '%s', '%s', '%s', '%s', '%s', '%s');" % args
        query = session.execute(call_sql)
        queryset = query.fetchall()

        group = ["科室", "诊疗组", "责任医生"] if self.type_ == "科室" else ["病区", "责任医生"]
        datarows = ["已归档病历数", "质控病历数", "总分", "甲级病历数", "甲级病历总分", "乙级病历数", "乙级病历总分", "丙级病历数", "丙级病历总分"]

        keys = ["总计"]  # 统计键用于去重
        result = {}  # 统计结果，只保存数据部分，初始值为空
        total = [0 for item in datarows]  # 总计

        for item in queryset:
            # 总计
            for di in range(len(datarows)):
                total[di] += item[len(group) + di]
            #
            for hi in range(len(group)):
                # 科室 不显示诊疗组
                if self.type_ == "科室" and not group_flag and hi == 1:
                    continue
                key = '||'.join([(item[i] or "") for i in range(hi + 1)])
                if key in keys:
                    for di in range(len(datarows)):
                        result[key][di] += item[len(group) + di]
                else:
                    keys.append(key)
                    result[key] = [item[len(group) + di] for di in range(len(datarows))]

        if result:
            result["总计"] = total

        res = []
        for key in keys:
            data = result.get(key)
            if not data:
                continue
            # [科室，诊疗组，责任医生，已归档病历数，质控病历数，总分，甲级病历数，甲级病历总分，乙级病历数，乙级病历总分，丙级病历数，丙级病历总分]
            # [病区，责任医生，已归档病历数，质控病历数，总分，甲级病历数，甲级病历总分，乙级病历数，乙级病历总分，丙级病历数，丙级病历总分]
            thirdNum = int(data[-2])  # 丙级病历数
            secondNum = int(data[-4])  # 乙级病历数
            firstNum = int(data[-6])  # 甲级病历数
            finishedNum = int(data[-8])  # 质控病历数
            archivedNum = int(data[-9])  # 归档病历数
            firstAvg = (data[-5] / firstNum) if firstNum else 0  # 甲级平均分 = 甲级总分/甲级病历数
            secondAvg = (data[-3] / secondNum) if secondNum else 0  # 乙级总分/乙级病历数
            thirdAvg = (data[-1] / thirdNum) if thirdNum else 0  # 丙级总分/丙级病历数
            thirdRate = (thirdNum / archivedNum) if archivedNum else 0  # 丙级病历占比
            secondRate = (secondNum / archivedNum) if archivedNum else 0  # 乙级病历占比
            firstRate = (firstNum / archivedNum) if archivedNum else 0  # 甲级病历占比
            sampleRate = (finishedNum / archivedNum) if archivedNum else 0  # 抽检率
            averageScore = (data[-7] / archivedNum) if archivedNum else 0  # 平均分

            title = (key + "||||").split("||")
            if self.type_ == "科室":
                res.append(ItemData(dept=title[0], group=title[1], attend=title[2], ward="",
                                    data=[archivedNum, finishedNum, averageScore, sampleRate, firstNum, firstAvg,
                                          firstRate, secondNum, secondAvg, secondRate, thirdNum, thirdAvg, thirdRate]))
            if self.type_ == "病区":
                res.append(ItemData(dept="", group="", ward=title[0], attend=title[1],
                                    data=[archivedNum, finishedNum, averageScore, sampleRate, firstNum, firstAvg,
                                          firstRate, secondNum, secondAvg, secondRate, thirdNum, thirdAvg, thirdRate]))
        return res

    def export_excel(self, session, header, file_name):
        """
        归档病历质量统计写excel
        :return:
        """
        group_flag = "诊疗组" in header
        data = self.stats(session, group_flag)

        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet()
        for i in range(len(header)):
            worksheet.write(0, i, header[i])

        row = 1
        for item in data:
            if item.attend:
                worksheet.write(row, 2 if group_flag else 1, item.attend)
            elif item.group:
                if group_flag:
                    worksheet.write(row, 1, item.group)
            else:
                worksheet.write(row, 0, item.ward if self.type_ == "病区" else item.dept)
            col = 3 if group_flag else 2
            # 统计数据
            for i in range(len(item.data)):
                worksheet.write(row, col + i, item.data[i])
            row += 1

        for col in range(len(header)):
            worksheet.set_column(0, col, 22)
        workbook.close()

    def detail(self, session, case_model, request, is_export=0):
        """
        归档病历质量统计明细
        """
        query = session.query(CaseArchiveExtend, case_model).\
            join(case_model, CaseArchiveExtend.caseid == case_model.caseId)
        if request.branch:
            query = query.filter(CaseArchiveExtend.branch == request.branch)
        if request.department:
            query = query.filter(CaseArchiveExtend.outdeptname.in_(request.department.split(",")))
        if request.group:
            query = query.filter(CaseArchiveExtend.medicalgroupname.in_(request.group.split(",")))
        if request.ward:
            query = query.filter(CaseArchiveExtend.wardname.in_(request.ward.split(",")))
        if request.attend:
            query = query.filter(CaseArchiveExtend.attendDoctor.in_(request.attend.split(",")))
        if request.startScore:
            query = query.filter(CaseArchiveExtend.score >= float(request.startScore))
        if request.endScore:
            query = query.filter(CaseArchiveExtend.score <= float(request.endScore))
        if request.finishedFlag:
            query = query.filter(CaseArchiveExtend.is_mq == {1: "是", 2: "否"}.get(request.finishedFlag, ""))
        if request.level:
            query = query.filter(
                CaseArchiveExtend.caselevel == {"甲级": "甲", "乙级": "乙", "丙级": "丙"}.get(request.level, request.level))
        if request.startTime:
            query = query.filter(CaseArchiveExtend.dischargetime >= request.startTime)
        if request.endTime:
            query = query.filter(CaseArchiveExtend.dischargetime <= request.endTime)
        total = query.count()
        if not is_export:
            start = request.start or 0
            size = request.size or 10
            query = query.slice(start, start + size)
        return total, query.all()

    def write_detail_excel(self, title, data, file_name):
        """
        归档病历质量统计明细写excel
        """
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet()
        for i in range(len(title)):
            worksheet.write(0, i, title[i])

        row = 1
        for item, case in data:
            # 病历号，姓名，入院日期，出院日期，（科室，[诊疗组]）/ 病区，责任医生，是否质控，病历等级，病历分数
            row_data = [case.inpNo or case.patientId or "", item.name or "",
                        item.admittime.strftime("%Y-%m-%d") if item.admittime else "",
                        item.dischargetime.strftime("%Y-%m-%d") if item.dischargetime else "", ]
            if self.type_ == "科室":
                row_data += [item.outdeptname or ""]
                if "诊疗组" in title:
                    row_data += [item.medicalgroupname or ""]
            if self.type_ == "病区":
                row_data += [item.wardname or ""]
            row_data += [item.attendDoctor or "", item.is_mq or "", item.caselevel or "", str(item.score or 0)]
            for col in range(len(row_data)):
                worksheet.write(row, col, row_data[col])
            row += 1

        workbook.close()
