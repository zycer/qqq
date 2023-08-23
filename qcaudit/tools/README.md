常用的操作

 - [x] 下载质控点配置模板
 - [x] 下载配置项设置模板 
 - [x] 导入质控点信息，包含强控标记，开启关闭
 - [x] 导入规则组设置
 - [x] 发送指定消息到队列 pub
 - [x] 发送指定消息到队列 f2q
 - [x] 获取队列中消息到文件 q2f
 - [x] 导出未对照文书自动对照结果
 - [x] 导入确认后的文书对照关系表
 - [ ] rerun 重抓数据
 - [ ] 导入手术字典和诊断字典数据
 - [ ] 初始化数据，重点病历标签等，检查数据库中数据异常的字典表
 - [ ] 导出数据，导出质控点报警列表，导出病历数据
 - [ ] 导入数据，导入病历数据到测试环境，导入字典数据到线上
 - [x] 导入质控评分表
 - [ ] 药品分类数据导入，抗生素，止痛，抗凝等
 - [ ] debug 显示病历号的数据，时间线
 - [ ] 日历维护表导出，增量导入
 - [ ] 用户管理 科室表，内外科关系


## 依赖 requirement
 - webargparse
 - streamlit

## 使用

参考 [webargparse](http://git.bdmd.com/server/infrastructure/webargparse) 项目

> python -m webargparse -m tools

docker run

> docker run -it -p 8503:8503 --entrypoint "" dockerdist.bdmd.com/qcaudit-api:2022.2.10.18.23.32 python3 -m webargparse -m tools

## 初始化数据

1. 规则组设置，5个规则组，加5个规则类别
2. 重点病历标签