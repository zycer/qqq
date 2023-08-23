#!/usr/bin/env python
# coding=utf-8
'''
Author: qiupengfei@rxthinking.com
Date: 2021-06-15 19:29:02


```yaml
name: 报表名称, 其实没什么用
fields: # 需要计算生成的列
    - name: "字段名称"
      hide: true|false  # 是否隐藏
      displayName: '实际展示名称"
      ignoreAcc: true|false, #汇总行忽略此列
      format: "格式化字符串， 对应python的格式化字符串，用于处理数字或日期的显示格式， 默认为%s"
      formular: "计算公式，用于支持平均数、百分数的情况, 格式'{fd1}/{fd2}'， 在python中计算”
groupFields: # 指定那几列是分组列，汇总时忽略这些列，汇总时按照分组顺序汇总所在层级的数据，分组列必须展示
    - name: "字段名称"
      hide: true|false #是否隐藏
      displayName: '展示名称'
      addAccRow: true|false #是否增加汇总
      accToColumn: true|false # 汇总行转列， 隐含合并前序单元格
      accRowFirst: true|false # 汇总行放在最前还是最后
      accTitle: "汇总行名称， 默认总计"
      mergeCells: true|false  #是否合并单元格， 合并单元格则此列之前全部合并，包括下一列产生的汇总列
      toColumn: true|fals # 暂未实现，只允许最后一个分组列行转列放到表头显示。隐含对此列求汇总并加到列上合并单元格
blankChar: "空白填充字符串，给前端API中合并单元格只是保留第一行，其他行使用此占位符"
```

# 支持的功能
1. 可以给任意分组级别增加汇总行。
2. 汇总行可以转成列加在分组列之后显示，表头一致
3. 最后一个分组列可以行转列显示，表头在原来基础上加(分组列内容)
4. 需要汇总的列，原始计算数据均需要存在，跟据公式计算汇总值。
5. 分组列支持合并单元格

'''
import enum
import sys
from collections import OrderedDict
import platform
import xlsxwriter
import openpyxl
import yaml
import logging

# logging.basicConfig(level=logging.INFO, format="[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")

MAX_NUMBER = 9999999999
MIN_NUMBER = -9999999999


class FieldBase(object):

    def __init__(self, name, displayName=None, format='%s', hide=False):
        # 字段名称
        self.name = name
        # 是否在展示时隐藏
        self.hide = hide
        # 展示名称
        self.displayName = displayName or name
        # 格式化字符串
        self.format = format

    def getValue(self, row, format=False):
        if not format:
            return row.get(self.name, '')
        else:
            return self.formatValue(row.get(self.name, ''))

    def formatValue(self, value):
        if not self.format:
            return value
        if value == None:
            value = 0.00
        # if not value and str(value) != "0" and str(value) != "0.0":
        #     return value
        return self.format % value

    def isGroupField(self):
        return False


class BIFormConfigField(FieldBase):

    def __init__(self, name,
                 hide=False, displayName=None, ignoreAcc=False, format='%s',
                 formular=None):
        super(BIFormConfigField, self).__init__(name, displayName, format, hide)
        # 汇总时忽略
        self.ignoreAcc = ignoreAcc
        # 计算公式, 注意unicode转换
        self.formular = formular

    def getValue(self, row, format=False):
        # 公式只计算一次
        if self.formular:
            value = eval(self.formular.format(**row))
            if not format:
                return value
            else:
                return self.formatValue(value)
        else:
            return super(BIFormConfigField, self).getValue(row, format=format)

    def isVirtual(self):
        return True if self.formular else False


class BIFormConfigGroupField(FieldBase):

    def __init__(self, name, displayName=None, addAccRow=False, accTitle='总计', accToColumn=False, toColumn=False,
                 format='%s', hide=False, accRowFirst=False, mergeCells=False):
        super(BIFormConfigGroupField, self).__init__(name, displayName, format, hide)
        # 增加汇总行
        self.addAccRow = addAccRow
        # 汇总行的标题
        self.accTitle = accTitle
        # 汇总行转到列, 添加在分组列之前, 隐含前一列的mergeCells = True
        self.accToColumn = accToColumn
        # 分组列展开到列, 只允许多个分组列的最后一列展开, 且隐含addAccRow和accToColumn都是True
        # TODO: 暂未实现
        self.toColumn = toColumn
        # 汇总行放在最前, False时在最后
        self.accRowFirst = accRowFirst
        # 是否合并单元格
        self.mergeCells = mergeCells
        if self.toColumn:
            self.addAccRow = True
            self.accToColumn = True

        # 下一分组
        self._nextGroupField = None
        # 行转列时此列的全部取值
        self.expandValues = []

    def statExpandValues(self, data):
        """最后一个分组列展开需要获取此列所有取值
        """
        self.expandValues = sorted(list(set([self.getValue(item) for item in data if not item.get('_is_acc_row')])))

    def setNextGroupField(self, fd):
        self._nextGroupField = fd
        if fd.accToColumn:
            self.mergeCells = True

    def getNextGroupField(self):
        return self._nextGroupField

    def getAccField(self, fd):
        """生成汇总行转列对应的列
        """
        return BIFormConfigField(
            self.name + '_' + fd.name,
            hide=fd.hide,
            displayName=fd.displayName,
            ignoreAcc=False,
            format=fd.format
        )

    def isGroupField(self):
        return True


class BIFormConfig(object):

    def __init__(self, name, fields, groupFields, blankChar=''):
        self.name = name
        # if not fields or not groupFields:
        #     raise ValueError('fields and groupFields cannot be null')

        self.fields = OrderedDict()
        for item in fields:
            self.fields[item.name] = item
        # 要合并单元格的字段按长度排序, 短的必须是长的的前缀, 要合并则从头开始合并
        mergeFields = []
        self.groupFields = OrderedDict()
        for i, item in enumerate(groupFields):
            self.groupFields[item.name] = item
            if i > 0:
                groupFields[i - 1].setNextGroupField(item)
        for i in range(0, len(groupFields)):
            if groupFields[i].mergeCells:
                mergeFields.append(tuple([fd.name for fd in groupFields[:i + 1]]))
        # 所有分组列都要合并单元格
        self.mergeFields = sorted(list(set([
            tuple(item) for item in mergeFields
        ])), key=lambda x: len(x))
        for i in range(0, len(self.mergeFields)):
            if i > 0:
                lastLength = len(self.mergeFields[i - 1])
                if self.mergeFields[i][:lastLength] != self.mergeFields[i - 1]:
                    raise ValueError('merge fields must container shortter one')
        self.blankChar = blankChar

    @property
    def GroupFieldList(self):
        return list(self.groupFields.values())

    @property
    def FieldList(self):
        return list(self.fields.values())

    @classmethod
    def fromJson(cls, js):
        fields = [
            BIFormConfigField(**item) for item in js.get('fields', [])
        ]
        groupFields = [
            BIFormConfigGroupField(**item) for item in js.get('groupFields', [])
        ]
        mergeFields = [item.split(',') for item in js.get('mergeFields', [])]
        return cls(
            name=js['name'],
            fields=fields,
            groupFields=groupFields,
        )

    def getNextAccFields(self, groupField):
        """若下一分组列需要汇总,且汇总行转到列, 则需要此函数.
           这里逻辑比较绕,是因为汇总行转列后是否合并单元格应该与前一列保持一致

        """
        if not groupField:
            return []
        gfd = groupField.getNextGroupField()
        if gfd and gfd.addAccRow and gfd.accToColumn:
            return [
                gfd.getAccField(fd) for fd in self.FieldList if not fd.hide and not fd.ignoreAcc
            ]
        return []

    @classmethod
    def fromYaml(cls, yamlContent):
        js = yaml.load(yamlContent, Loader=yaml.FullLoader)
        return cls.fromJson(js)

    def getAccRow(self, groupField, rows):
        """获取汇总行

        Args:
            groupField ([type]): [description]
            rows ([type]): [description]
        """
        # 当前分组字段之前的分组字段原样保留, 其他分组字段留空
        found = False
        titleAdded = False
        row = {}
        for fd in self.groupFields.values():
            if fd.name == groupField.name:
                row[fd.name] = groupField.accTitle
                found = True
            elif not found:
                row[fd.name] = rows[0][fd.name]
            else:
                row[fd.name] = self.blankChar
        for fdName, fd in self.fields.items():
            if fd.ignoreAcc:
                row[fdName] = self.blankChar
            else:
                row[fdName] = sum([r[fdName] for r in rows])
        # 为汇总行计算虚拟列
        for fd in self.fields.values():
            if fd.isVirtual():
                row[fd.name] = fd.getValue(row)
            # if groupField.accToColumn:
            vfd = groupField.getAccField(fd)
            for r in rows:
                r[vfd.name] = row[fd.name]
        # 如果最后一列展开, 那么汇总行前移
        expandColumn = self.getExpandGroupColumn()
        if expandColumn:
            for fd in self.fields.values():
                vfd = expandColumn.getAccField(fd)
                row[vfd.name] = row[fd.name]
                # row[fd.name] = self.blankChar
        row['_is_acc_row'] = True

        return row

    def getExpandGroupColumn(self):
        """获取要展开到列的分组列
        """
        if not self.GroupFieldList:
            return
        field = self.GroupFieldList[-1]
        if field.toColumn:
            return field
        else:
            return None

    def getDisplayHeaders(self, withAccCol=False):
        """获取最终展示的列,
            withAccCol: 是否包含汇总行转列得到的列
        """
        headers = []
        for item in self.groupFields.values():
            if not item.toColumn:
                headers.append(item)
            if withAccCol:
                headers.extend(self.getNextAccFields(item))
        expandColumn = self.getExpandGroupColumn()
        if not expandColumn:
            for item in self.fields.values():
                if not item.hide:
                    headers.append(item)
        else:
            for val in expandColumn.expandValues:
                for item in self.fields.values():
                    if not item.hide:
                        headers.append(
                            BIFormConfigField(
                                name='%s|%s' % (item.name, val),
                                displayName='%s(%s)' % (item.name, val),
                                hide=False,
                                format=item.format
                            )
                        )

        return headers

    def getField(self, name):
        """根据名称获取列
        """
        if name in self.groupFields:
            return self.groupFields[name]
        else:
            return self.fields[name]


class BIDataProcess(object):

    def __init__(self, formConfig, data):
        """

        Args:
            formConfig (BIFormConfig): 表格配置信息
            data (Iterable): 从数据库得到的统计数据,list或deque,每一行是一个dict
        """
        self.formConfig = formConfig
        self.data = data
        self._processed = False

    def getMergeKey(self, mergeField, row):
        return tuple([row[k] for k in mergeField])

    def toWeb(self, sortBy=None, start=0, size=0):
        """
        生成给web展示用的二维表数据
        :param sortBy: (tuple, optional) 排序列. Defaults to None.
        :param start:
        :param size:
        :return: (表头+展示名称, 字典的列表)
        """
        self.preProcess(sortBy)
        headers = self.formConfig.getDisplayHeaders()
        if self.formConfig.mergeFields:
            # 先遍历一遍数据, 给每个mergeField生成两个标记列(分组计数和分组序号)
            firstRowIndex = [[-1, None]] * len(self.formConfig.mergeFields)  # 每个mergeField一个元素, 记录上一个index和对应的key
            for i, row in enumerate(self.data):
                mergeField = None
                for j, mf in enumerate(self.formConfig.mergeFields):
                    mergeKey = self.getMergeKey(mf, row)
                    if firstRowIndex[j][0] < 0 or firstRowIndex[j][1] != mergeKey:
                        firstRowIndex[j] = [i, mergeKey]
                    else:
                        mergeField = mf
                if mergeField:
                    for fd in mergeField:
                        row[fd] = self.formConfig.blankChar
                        gfd = self.formConfig.groupFields.get(fd)
                        if gfd:
                            for f in self.formConfig.getNextAccFields(gfd):
                                row[f.name] = self.formConfig.blankChar

        result = []
        headers = self.formConfig.getDisplayHeaders(withAccCol=True)
        for row in self.data:
            tmp = {
                k.name: k.getValue(row, format=True) for k in headers
            }
            result.append(tmp)
        if size:
            result = result[start:start + size]
        return headers, result

    def toExcel(self, path=None, sortBy=None, column_width=None, sheet=None, sheet_name=None):
        """
        生成excel到指定的路径path
        :param path: excel文件绝对路径+名
        :param sortBy: 排序列. Defaults to None.
        :param column_width: (list[column, width]): 设置某一列宽度
        :param sheet: 指定sheet时不用重新创建excel对象
        :param sheet_name: 创建sheet指定名字
        :return:
        """
        self.preProcess(sortBy)
        self.writeExcel(path, column_width, sheet, sheet_name)

    def writeExcel(self, path=None, column_width=None, sheet=None, sheet_name=None):
        """写入excel, 并处理合并单元格

        Args:
            :param path:
            :param column_width: 某一列宽度 [列索引, 要设置的宽度]
            :param sheet:
            :param sheet_name:
        """
        data = self.data
        headers = self.formConfig.getDisplayHeaders()
        formatTop = None
        formatOther = None
        workbook = None
        if not sheet:
            workbook = xlsxwriter.Workbook(path)
            sheet = workbook.add_worksheet(name=sheet_name)
            formatTop = workbook.add_format({'border': 1, 'bold': True, 'text_wrap': True})
            formatOther = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
        sheet.set_column(0, 100, width=11)
        if column_width:
            sheet.set_column(0, column_width[0] - 1, width=11)
            sheet.set_column(column_width[0], column_width[0], width=column_width[1])
            sheet.set_column(column_width[0] + 1, 100, width=11)
        # 写表头
        colIndex = 0
        for i, fd in enumerate(headers):
            # print(value)
            sheet.write(0, colIndex, fd.displayName, formatTop)
            colIndex += 1
            if fd.isGroupField():
                for f in self.formConfig.getNextAccFields(fd):
                    sheet.write(0, colIndex, f.displayName, formatTop)
                    colIndex += 1

        if self.formConfig.mergeFields:
            # 先遍历一遍数据, 给每个mergeField生成两个标记列(分组计数和分组序号)
            firstRowIndex = [[-1, None, 0]] * len(self.formConfig.mergeFields)  # 每个mergeField一个元素, 记录上一个index和对应的key
            dataLength = len(data)
            for i, row in enumerate(data):
                for j, mf in enumerate(self.formConfig.mergeFields):
                    mergeKey = self.getMergeKey(mf, row)
                    if firstRowIndex[j][0] < 0 or firstRowIndex[j][1] != mergeKey:
                        if firstRowIndex[j][0] >= 0:
                            # 记录上一个key出现的次数
                            for k in range(firstRowIndex[j][0], i):
                                data[k]['_mf_%s_cnt' % j] = firstRowIndex[j][2]
                        firstRowIndex[j] = [i, mergeKey, 1]
                        row['_mf_%s_seq' % j] = 1
                    else:
                        tmp = firstRowIndex[j]
                        firstRowIndex[j] = [tmp[0], mergeKey, tmp[2] + 1]
                        row['_mf_%s_seq' % j] = tmp[2] + 1
                    if i == dataLength - 1:
                        if firstRowIndex[j][0] >= 0:
                            # 记录上一个key出现的次数
                            for k in range(firstRowIndex[j][0], dataLength):
                                data[k]['_mf_%s_cnt' % j] = firstRowIndex[j][2]
            # 开始写excel
            for i, row in enumerate(data):
                realIndex = 0
                for colIndex, col in enumerate(headers):
                    groupField = None
                    if col.isGroupField():
                        groupField = col
                    # 获取colIndex所属的mergeField
                    mfIndex = -1
                    field = None
                    for j, mf in enumerate(self.formConfig.mergeFields):
                        if colIndex < len(mf):
                            mfIndex = j
                            field = mf
                            break
                    # 不在合并字段中, 直接输出
                    if mfIndex < 0:
                        sheet.write(i + 1, realIndex, col.getValue(row, format=True), formatOther)
                        realIndex += 1
                        for fd in self.formConfig.getNextAccFields(groupField):
                            sheet.write(i + 1, realIndex, fd.getValue(row, format=True), formatOther)
                            realIndex += 1
                    # key只出现一次,也不需要合并,直接输出
                    elif row['_mf_%s_cnt' % mfIndex] <= 1:
                        sheet.write(i + 1, realIndex, col.getValue(row, format=True), formatOther)
                        realIndex += 1
                        for fd in self.formConfig.getNextAccFields(groupField):
                            sheet.write(i + 1, realIndex, fd.getValue(row, format=True), formatOther)
                            realIndex += 1
                    # key出现多次, 需要合并
                    else:
                        if row['_mf_%s_seq' % mfIndex] == 1:
                            sheet.merge_range(
                                i + 1, realIndex, i + row['_mf_%s_cnt' % mfIndex], realIndex,
                                col.getValue(row, format=True), formatOther
                            )
                        realIndex += 1
                        for fd in self.formConfig.getNextAccFields(groupField):
                            if row['_mf_%s_seq' % mfIndex] == 1:
                                sheet.merge_range(
                                    i + 1, realIndex, i + row['_mf_%s_cnt' % mfIndex], realIndex,
                                    fd.getValue(row, format=True), formatOther)
                            realIndex += 1
        else:
            # 正常输出excel
            for i, row in enumerate(data):
                for colIndex, col in enumerate(headers):
                    sheet.write(i + 1, colIndex, col.formatValue(row[col.name]), formatOther)
        if workbook:
            workbook.close()

    def preProcess(self, sortBy=[]):
        """预处理
        """
        if self._processed:
            return
        # 计算所有虚拟列
        for row in self.data:
            for fd in self.formConfig.fields.values():
                if fd.isVirtual():
                    row[fd.name] = fd.getValue(row)

        # 排序时只有最后一个分组列可以变动
        # tmp = [(gf.name, 1) for gf in self.formConfig.GroupFieldList[:-1]]
        # if sortBy:
        #    for fd, _ in sortBy:
        #        if fd not in self.formConfig.fields:
        #            raise ValueError("只有指标字段可以排序")
        #    sortBy = tmp + sortBy
        # else:
        #    sortBy = tmp
        # 按分组列排序
        def getSortKey1(x):
            result = []
            for fd in self.formConfig.GroupFieldList:
                fdName = fd.name
                result.append(x[fdName])
            return tuple(result)

        if sortBy:
            self.data.sort(key=getSortKey1)

        # 增加汇总行
        # 要添加的行记住自己要插入的位置, 在生成后再一次插入
        # (要添加的行, 插入在此位置之前, 分组顺序)
        addRows = []
        firstRowIndex = [[-1, None]] * len(self.formConfig.groupFields)
        dataLength = len(self.data)
        accRowDict = {}
        for i, row in enumerate(self.data):
            for j, groupField in enumerate(self.formConfig.groupFields.values()):
                if groupField.addAccRow:
                    groupValue = tuple([
                        row[fd.name] for fd in self.formConfig.GroupFieldList[:j]
                    ])
                    # 处理前一个分组的汇总
                    if firstRowIndex[j][0] >= 0 and firstRowIndex[j][1] != groupValue:
                        accRow = self.formConfig.getAccRow(
                            groupField, self.data[firstRowIndex[j][0]:i]
                        )
                        if not groupField.accToColumn:
                            if groupField.accRowFirst:
                                addRows.append((accRow, firstRowIndex[j][0], j))
                            else:
                                addRows.append((accRow, i, -j))
                        accRowDict[firstRowIndex[j][1]] = accRow
                    if firstRowIndex[j][0] < 0 or firstRowIndex[j][1] != groupValue:
                        firstRowIndex[j] = [i, groupValue]

                    # 已经是最后一个元素
                    if i == dataLength - 1:
                        accRow = self.formConfig.getAccRow(
                            groupField, self.data[firstRowIndex[j][0]:]
                        )
                        accRowDict[groupValue] = accRow
                        if not groupField.accToColumn:
                            if groupField.accRowFirst:
                                # 大类的总计放在小类的前面
                                addRows.append((accRow, firstRowIndex[j][0], j))
                            else:
                                # 大类的总计放在小类的后面
                                addRows.append((accRow, i + 1, -j))

        # 开始插入行
        if addRows:
            addRows = sorted(addRows, key=lambda x: (x[1], x[2]))
            newData = []
            j = 0

            for i, row in enumerate(self.data):
                while j < len(addRows) and i >= addRows[j][1]:
                    addRow = addRows[j][0]
                    newData.append(addRow)
                    j += 1
                newData.append(row)
            while j < len(addRows):
                newData.append(addRows[j][0])
                j += 1
            self.data = newData

        # 处理最后一个分组列的行转列问题
        # 得到列中所有的值
        expandColumn = self.formConfig.getExpandGroupColumn()
        if expandColumn:
            expandColumn.statExpandValues(self.data)
            newData = []
            mergeField = [fd.name for fd in self.formConfig.GroupFieldList[:-1]]
            lastMergeKey = None
            lastRow = None
            for row in self.data:
                mk = self.getMergeKey(mergeField, row)
                if mk != lastMergeKey:
                    if lastRow:
                        newData.append(lastRow)
                    lastRow = row
                    lastMergeKey = mk
                for field in self.formConfig.FieldList:
                    lastRow[
                        '%s|%s' % (field.name, expandColumn.getValue(row))
                        ] = field.getValue(row)
            if lastRow:
                newData.append(lastRow)
            self.data = newData

        # print(json.dumps(self.data, ensure_ascii=False,  indent=4))
        # 排序, 如果求了汇总，则需要根据汇总结果排序
        def getSortKey(row):
            sortKeys = []
            groupFieldCount = len(self.formConfig.groupFields)
            groupFieldList = self.formConfig.GroupFieldList
            for j, groupField in enumerate(groupFieldList):
                # 此列求了汇总，则先根据汇总行的数值来排序
                groupValue = tuple([
                    row[fd.name] for fd in groupFieldList[:j]
                ])
                # print(groupValue)
                if groupField.addAccRow:
                    accRow = accRowDict.get(groupValue)
                    if accRow:
                        for fd, direction in sortBy:
                            field = self.formConfig.fields[fd]
                            val = field.getValue(accRow)
                            # 只有数字支持方向
                            if not isinstance(val, (int, float)):
                                sortKeys.append(val)
                            else:
                                sortKeys.append(val * direction)
                    else:  # 本身是汇总列，且比当前分组级别高，根据上一个分组列将汇总行放在最前还是最后来设置排序字段
                        lastField = self.formConfig.GroupFieldList[j - 1]
                        sortKeys.append(MIN_NUMBER if lastField.accRowFirst else MAX_NUMBER)

                # 此列汇总的实际上是前一列的数字，例如(科室分类、科室)，对科室列汇总得到的实际上是对应科室分类的总和
                # 因此对于汇总值相同的行，按照前一列的名称来排序
                if j > 0:
                    lastField = self.formConfig.GroupFieldList[j - 1]
                    value = lastField.getValue(row)
                    # if lastField.addAccRow and lastField.accRowFirst and value == lastField.accTitle:
                    #    sortKeys.append(MIN_NUMBER)
                    # elif lastField.addAccRow and not lastField.accRowFirst and value == lastField.accTitle:
                    #    sortKeys.append(MAX_NUMBER)
                    # else:
                    #    sortKeys.append(hash(value) % 1000)
                    sortKeys.append(value)

            if row.get('_is_acc_row'):
                lastField = self.formConfig.GroupFieldList[-1]
                sortKeys.append(MIN_NUMBER if lastField.accRowFirst else MAX_NUMBER)
            else:
                for fd, direction in sortBy:
                    field = self.formConfig.fields[fd]
                    val = field.getValue(row)
                    # if not val:
                    #    val = MIN_NUMBER if direction > 0 else MAX_NUMBER
                    # 只有数字支持方向
                    if not isinstance(val, (int, float)):
                        sortKeys.append(val)
                    else:
                        sortKeys.append(val * direction)
            # print(sortKeys, row)
            return tuple(sortKeys)

        if sortBy:
            self.data = sorted(self.data, key=getSortKey)

        self._processed = True


def main():
    import json
    data = json.loads('''[
        {"科室分类": "内科", "科室": "呼吸内科", "月份": "1月", "总数": 6, "优秀病历": 4},
        {"科室分类": "内科", "科室": "呼吸内科", "月份": "2月", "总数": 6, "优秀病历": 4},
        {"科室分类": "内科", "科室": "消化内科", "月份": "1月", "总数": 4, "优秀病历": 3},
        {"科室分类": "内科", "科室": "消化内科", "月份": "2月", "总数": 4, "优秀病历": 3},
        {"科室分类": "内科", "科室": "心内科", "月份": "2月", "总数": 5, "优秀病历": 5},
        {"科室分类": "外科", "科室": "普外科", "月份": "3月", "总数": 10, "优秀病历": 5},
        {"科室分类": "外科", "科室": "普外科", "月份": "2月", "总数": 10, "优秀病历": 2},
        {"科室分类": "外科", "科室": "普外科", "月份": "1月", "总数": 12, "优秀病历": 2},
        {"科室分类": "外科", "科室": "胸外科", "月份": "2月", "总数": 5, "优秀病历": 3}
    ]''')
    yamlConfig = '''
name: test
fields:
    - name: 总数
    - name: 优秀病历
    - name: 优秀率
      formular: '{优秀病历}*1.0/{总数}'
      format: '%0.2f'
groupFields:
    - name: 科室分类
      addAccRow: true
      accRowFirst: true
      accTitle: 全院合计
      mergeCells: true
    - name: 科室
      addAccRow: true
      accToColumn: false
      accRowFirst: true
      accTitle: '总计'
      mergeCells: true
    - name: 月份
      toColumn: false
'''
    cfg = BIFormConfig.fromYaml(yamlConfig)
    processor = BIDataProcess(cfg, data)
    processor.toExcel(path='test.xlsx', sortBy=[(u'平均分', -1)])
    header, result = processor.toWeb(sortBy=[(u'平均分', -1)])  # [(u'总数', 1), (u'优秀率', -1)], size=300)
    for item in result:
        print(json.dumps(item, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
