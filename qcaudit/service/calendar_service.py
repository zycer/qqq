# #!/usr/bin/env python3
# '''
# 日历维护接口
# '''

# import logging
# import arrow

# from iyoudoctor.hosp.qc.v3.qcaudit.service_message_pb2 import CommonResponse, GetCalendarResponse


# class CalendarService:

#     def __init__(self, context):
#         self.context = context

#     def GetCalendar(self, request, context):
#         """获取日历维护数据
#         """
#         """根据时间段获取日历信息
#         参数：开始时间和结束时间,如果没有开始时间参数，默认从2020年1月1号开始
#         """
#         response = GetCalendarResponse()

#         start = arrow.get(request.startTime).to('+08:00').strftime('%Y-%m-%d %H:%M:%S')
#         end = arrow.get(request.endTime).to('+08:00').strftime('%Y-%m-%d %H:%M:%S')

#         with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
#             for d in self.context.getCalendarRepository("hospital").getList(session, start, end):
#                 protoItem = response.data.add()
#                 protoItem.date = arrow.get(d.date).strftime('%Y-%m-%dT%H:%M:%SZ')
#                 protoItem.isWorkday = d.isWorkday == 1
#         return response

#     def SetCalendar(self, request, context):
#         """设置日历信息
#         """
#         response = CommonResponse()

#         data = [{'date': arrow.get(info.date).to('+08:00').strftime('%Y-%m-%d'), 'isWorkday': info.isWorkday} for info in request.data]

#         try:
#             with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
#                 self.context.getCalendarRepository("hospital").upsert(session, data)
#             response.isSuccess = True
#         except Exception as e:
#             logging.error(e)
#         return response


