# #!/usr/bin/env python3
# '''
# IP黑白名单接口
# '''

# import logging
# import arrow

# from iyoudoctor.hosp.qc.v3.qcaudit.service_message_pb2 import CommonResponse, GetIpBlockListResponse

# from qcaudit.domain.ipaddr.ip_rule import IpRule


# class IpBlockService:

#     def __init__(self, context):
#         self.context = context

#     def GetIpBlockList(self, request, context):
#         """获取医生端ip黑白名单列表
#         """
#         response = GetIpBlockListResponse()

#         with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
#             handler = session.query(IpRule)
#             if request.ip:
#                 handler = handler.filter_by(ip=request.ip)
#             if request.rule:
#                 handler = handler.filter_by(rule=request.rule)
#             # 列表总数
#             response.total = handler.count()
#             # 黑白名单列表
#             for r in handler.slice(request.start, request.start+request.size).all():
#                 protoItem = response.data.add()
#                 protoItem.id = r.id
#                 protoItem.ip = r.ip or ''
#                 protoItem.rule = r.rule or 0
#         return response

#     def UpdateIpBlock(self, request, context):
#         """创建或修改医生端ip黑白名单
#         """
#         response = CommonResponse()
#         if not request.ip:
#             return response
#         with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
#             rule = session.query(IpRule).filter_by(ip=request.ip).first()
#             if rule:
#                 rule.rule = request.rule
#             else:
#                 session.add(IpRule(ip=request.ip, rule=request.rule or 0))
#                 session.commit()
#             response.isSuccess = True
#         return response

#     def DeleteIpBlock(self, request, context):
#         """删除黑白名单中ip记录
#         """
#         response = CommonResponse()
#         if not request.id:
#             return response
#         with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
#             session.query(IpRule).filter(IpRule.id == request.id).delete()
#             session.commit()
#             response.isSuccess = True
#         return response


