from . import *
from qcaudit.env_config.pre_req import *
from qcaudit.common.const import *
from .qc_util import QCUtil
from qcaudit.service.protomarshaler import *
from qcaudit.config import Config
import arrow
from qcaudit.domain.dict.qcitem import QcItemRule
from qcaudit.domain.qcgroup.qcitem_req import GetItemsListRequest
from qcaudit.domain.qcgroup.qcgroup import QcCategory, QcCateItems
from itertools import groupby


class CreateQCItem(MyResource):

    @pre_request(request, CreateQCItemReq)
    def post(self):
        """创建质控项接口
        """
        isExist = self.context.getQcItemRepository('hospital').queryCodeIsExist(request.code)
        if not isExist:
            return get_error_resp("质控点编号已存在!")
        qcItem = {
            'code': request.code or '',
            'requirement': request.requirement or '',
            'instruction': request.instruction or '',
            'standard_emr': request.emrName or '0',
            'linkEmr': ','.join(request.linkEmr) or '',
            'rule': request.rule,
            'created_at': arrow.utcnow().to('+08:00').naive,
            'updated_at': arrow.utcnow().to('+08:00').naive,
            'is_deleted': 0,
            'operator_id': request.operatorId,
            'operator_name': request.operatorName,
            'type': request.type or 1,  # 专科专病类别
            'departments': ','.join(request.departments),
            'disease': ','.join(request.disease),
            'approve_status': 2,  # 默认已确认
            'flexTipFlag': 1,  # 最初用于控制显示 problem.reason or qcItem.instruction, TODO 删掉这个字段
            'custom': 1,  # 人工添加
            'enable': 2,  # 启用
            'tags': '',
            'counting': 1,
            'veto': 0,   # 默认非强控
            'category': request.category or 0,  # 时效性等类型，默认无
        }
        rule_dict = {
            "field": request.remindInfo.get("field") or "",
            'instruction': request.instruction or '',
            "firstHour": float(request.remindInfo.get("firstHour") or 0),
            "overHour": float(request.remindInfo.get("overHour") or 0),
            "includeQuery": request.includeQuery or "",
            "excludeQuery": request.excludeQuery or "",
        }
        application = self.context.getCaseApplication("hospital")
        qcItem = QcItem.newObject(application.app, **qcItem)
        with application.app.mysqlConnection.session() as session:
            self.context.getQcItemRepository('hospital').add(session, qcItem)
            session.commit()
            if not request.code:
                qcItem.setModel(code='LS' + str(qcItem.getId()))
            rule_dict["qcItemId"] = qcItem.getId()
            rule_dict["qcItemCode"] = qcItem.model.code
            rule = QcItemRule.newObject(application.app, **rule_dict)
            session.add(rule)
            session.commit()
        self.context.getQcItemRepository('hospital').sendReload()
        return g.result


class UpdateQCItem(MyResource):

    @pre_request(request, CreateQCItemReq)
    def put(self):
        """编辑质控点
        """
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            rows = self.context.getQcItemRepository('hospital').getList(session, GetItemsListRequest(id=request.id))
            if rows:
                item = rows[0]
                if item.custom:
                    if request.code and request.code != item.code:
                        tmp = self.context.getQcItemRepository('hospital').getList(session, GetItemsListRequest(code=request.code))
                        if tmp:
                            return get_error_resp('质控点编号已被占用')
                    item.setModel(
                        requirement=request.requirement,
                        instruction=request.instruction,
                        standard_emr=request.emrName,
                        type=request.type,
                        departments=','.join(request.departments),
                        disease=','.join(request.disease),
                        category=request.category or 0,
                    )
                    rule_dict = {
                        "field": request.remindInfo.get("field") or "",
                        'instruction': request.instruction or '',
                        "firstHour": float(request.remindInfo.get("firstHour") or 0),
                        "overHour": float(request.remindInfo.get("overHour") or 0),
                        "includeQuery": request.includeQuery or "",
                        "excludeQuery": request.excludeQuery or "",
                    }
                    self.context.getQcItemRepository('hospital').updateRule(session, item.id, rule_dict)
                else:
                    g.result["message"] = '非人工添加的质控点'
                session.commit()
        self.context.getQcItemRepository('hospital').sendReload()
        return g.result


class EnableQCItem(MyResource):

    @pre_request(request, ["items:list"])
    def put(self):
        """停用启用质控点
        """
        application = self.context.getCaseApplication('hospital')
        try:
            with application.app.mysqlConnection.session() as session:
                for item in request.items:
                    self.context.getQcItemRepository('hospital').enableItem(session, item["id"], item["enable"], item["enableType"])
            self.context.getQcItemRepository('hospital').sendReload()
        except Exception as e:
            logging.exception(e)
        return g.result


class DeleteQCItem(MyResource):

    @pre_request(request, ["id:int", "operatorId", "operatorName"])
    def delete(self, id=0):
        """删除单个质控点
        """
        request.id = id
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            self.context.getQcItemRepository('hospital').deleteItems(session, [request.id])
            self.context.getQcGroupRepository('hospital').deleteQcCateItemsByItem(session, [request.id])
        return g.result


class GetQCItem(MyResource):
    
    @pre_request(request, ["id:int"])
    def get(self, id=0):
        """质控点详情
        """
        request.id = id
        response = {"data": {"departments": [], "disease": []}}
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            req = GetItemsListRequest(id=request.id)
            rows = self.context.getQcItemRepository('hospital').getList(session, req)
            if rows:
                item = rows[0]
                unmarshalQcItem(item, response["data"])
        return response


class ListQCItem(MyResource):

    @pre_request(request, CreateQCItemReq)
    def get(self):
        """质控点列表
        """
        response = {"items": []}
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            params = ["code", "requirement", "instruction", "emrName", "type", "department",
                      "disease", "status", "custom", "enable", "start", "size", "category", "enableType"]
            req = {c: getattr(request, c) for c in params}
            req = GetItemsListRequest(**req)
            repo = self.context.getQcItemRepository('hospital')
            if req.disease:
                # 将诊断编码转成诊断名
                req.disease = repo.getDiseaseName(req.disease)
            # total
            response["total"] = repo.count(session, req)
            # rows
            rows = repo.getList(session, req)
            if rows:
                for row in rows:
                    protoItem = {"departments": [], "disease": []}  # response.items.add()
                    unmarshalQcItem(row, protoItem)
                    response["items"].append(protoItem)
        return response


class ApproveQCItem(MyResource):

    @pre_request(request, ["items:list", "operator"])
    def post(self):
        """确认
        """
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            for item in request.items:
                self.context.getQcItemRepository('hospital').approveItem(session, item)
        return g.result


class DeleteQCItems(MyResource):

    @pre_request(request, ["itemsId:list"])
    def post(self):
        """批量删除
        """
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            self.context.getQcItemRepository('hospital').deleteItems(session, request.itemsId)
            self.context.getQcGroupRepository('hospital').deleteQcCateItemsByItem(session, request.itemsId)
        return g.result


class ExportQCItems(MyResource):

    @pre_request(request, CreateQCItemReq)
    def post(self):
        """质控点列表导出
        """
        # todo 未实现
        return g.result


class GetQcGroup(MyResource):

    @pre_request(request, ["name"])
    def get(self):
        """规则组列表
        """
        response = {"items": []}
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            for group in self.context.getQcGroupRepository('hospital').getGroups(session, request.name):
                protoItem = {}  # response.items.add()
                protoItem["id"] = group.id
                protoItem["name"] = group.name
                protoItem["count"] = len(group.items)
                response["items"].append(protoItem)
        return response


class GetQcGroupItem(MyResource):

    @pre_request(request, GetQcGroupItemReq)
    def get(self):
        """规则组质控点查询
        inside == 1 规则组中包含的质控项
        inside == 2 规则组以外的质控项
        """
        response = {"data": [], "total": 0}
        if not request.id:
            return get_error_resp("id can not be empty.")
        application = self.context.getCaseApplication('hospital')
        req_start = (request.page - 1) * request.count
        with application.app.mysqlConnection.session() as session:
            if request.inside == 1:
                qcItems = {}
                for row in self.context.getQcItemRepository('hospital').getList(session, GetItemsListRequest()):
                    if row:
                        qcItems[row.id] = row
                rows = self.context.getQcGroupRepository('hospital').getQcCateItems(session, groupId=request.id)
                response["total"] = len(rows)
                index = 0
                for item in rows:
                    index += 1
                    if index <= req_start or len(response["data"]) >= request.count or not qcItems.get(item.itemId):
                        continue
                    qcItem = qcItems.get(item.itemId)
                    protoItem = {}  # response.data.add()
                    protoItem["id"] = qcItem.id
                    protoItem["code"] = qcItem.code
                    protoItem["name"] = qcItem.requirement
                    protoItem["maxScore"] = item.maxScore
                    protoItem["score"] = item.score
                    response["data"].append(protoItem)
            elif request.inside == 2:
                inside_items = [row.itemId for row in self.context.getQcGroupRepository('hospital').getQcCateItems(session, groupId=request.id)]
                index = 0
                for row in self.context.getQcItemRepository('hospital').\
                        getList(session, GetItemsListRequest(enable=2, requirement=request.itemName)):
                    if not row or row.id in inside_items:
                        continue
                    index += 1
                    response["total"] += 1
                    if index <= req_start or len(response["data"]) >= request.count:
                        continue
                    protoItem = {}  # response.data.add()
                    protoItem["id"] = row.id
                    protoItem["code"] = row.code
                    protoItem["name"] = row.requirement
                    response["data"].append(protoItem)
        return response


class GetQcCategory(MyResource):

    @pre_request(request, ["groupId:int", "type:int", "input"])
    def get(self):
        """规则组-文书类别
        """

        def build_sub_category_tree(node, categories, qcitems):
            # 构造质控规则组文书类别返回结构
            parentId = node["id"]
            for cate in categories:
                if cate.parentId == parentId:
                    subNode = {"subCategory": [], "items": []}  # node.subCategory.add()
                    subNode["id"] = cate.id
                    subNode["name"] = cate.name
                    subNode["maxScore"] = cate.maxScore
                    build_sub_category_tree(subNode, categories, qcitems)
                    node["subCategory"].append(subNode)
            if qcitems:
                for qci in qcitems:
                    if qci.categoryId == parentId:
                        tmp = {}  # node.items.add()
                        unmarshalCateItem(tmp, qci)
                        node["items"].append(tmp)
                        
        def unmarshalCateItem(protoModel, qciModel):
            # 质控点信息
            if not qciModel:
                return
            protoModel["id"] = qciModel.id
            protoModel["categoryId"] = qciModel.categoryId
            protoModel["itemId"] = str(qciModel.itemId)
            protoModel["name"] = qciModel.qcItemModel.requirement if qciModel.qcItemModel else ''
            protoModel["maxScore"] = qciModel.maxScore
            protoModel["score"] = qciModel.score
        
        response = {"data": []}
        application = self.context.getCaseApplication('hospital')
        with application.app.mysqlConnection.session() as session:
            data = self.context.getQcGroupRepository('hospital').getQcCategory(session, request.groupId)
            items = self.context.getQcGroupRepository('hospital').getQcCateItems(session, request.groupId, withItem=True)
            response["total"] = len(data) if data else 0
            for c in data:
                if c.parentId == 0:
                    protoItem = {"subCategory": [], "items": []}  # response.data.add()
                    protoItem["id"] = c.id
                    protoItem["name"] = c.name
                    protoItem["maxScore"] = c.maxScore
                    build_sub_category_tree(protoItem, categories=data, qcitems=(items if request.type else None))
                    response["data"].append(protoItem)
            if request.type == 1:
                response["total"] = len(items)
                zeroProtoItem = None
                for item in items:
                    if item.categoryId == 0 and not zeroProtoItem:
                        zeroProtoItem = {"subCategory": [], "items": []}  # response.data.add()
                        zeroProtoItem["name"] = "自定义质控点"
                        zeroProtoItem["maxScore"] = 100
                    if item.categoryId == 0:
                        protoItem = {}  # zeroProtoItem.items.add()
                        unmarshalCateItem(protoItem, item)
                        zeroProtoItem["items"].append(protoItem)
                    if zeroProtoItem:
                        response["data"].append(zeroProtoItem)
        return response

    @pre_request(request, AddQcCategoryReq)
    def post(self):
        """新增文书类别
        """
        category = {
            'groupId': request.groupId or 0,
            'parentId': request.parent or 0,
            'name': request.name or '',
            'maxScore': request.maxScore or 0,
            'created_at': arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
            'is_deleted': 0,
        }
        application = self.context.getCaseApplication("hospital")
        category = QcCategory.newObject(application.app, **category)
        with application.app.mysqlConnection.session() as session:
            self.context.getQcItemRepository('hospital').add(session, category)
        return g.result


class EditQcCategory(MyResource):

    @pre_request(request, ["id:int", "name", "maxScore:int"])
    def put(self, id=0):
        """编辑规则组文书类别
        """
        request.id = id
        if not request.id:
            return get_error_resp("id can not be empty.")
        application = self.context.getCaseApplication("hospital")
        with application.app.mysqlConnection.session() as session:
            rows = self.context.getQcGroupRepository('hospital').getQcCategory(session, cid=request.id)
            item = rows[0] if rows and rows[0] else None
            if item and request.name:
                item.name = request.name
            item.maxScore = request.maxScore or 0
        return g.result

    @pre_request(request, ["id:int"])
    def delete(self, id=0):
        """删除规则组文书类别
        """
        request.id = id
        if not request.id:
            return get_error_resp("id can not be empty.")
        application = self.context.getCaseApplication("hospital")
        with application.app.mysqlConnection.session() as session:
            rows = self.context.getQcGroupRepository('hospital').getQcCategory(session, cid=request.id)
            item = rows[0] if rows and rows[0] else None
            if item:
                item.is_deleted = 1
        return g.result
    

class AddQcCategoryItem(MyResource):
    
    @pre_request(request, ["categoryId", "itemsId:list"])
    def post(self):
        """质控点添加到规则组文书类别
        """
        application = self.context.getCaseApplication("hospital")
        with application.app.mysqlConnection.session() as session:
            rows = self.context.getQcGroupRepository('hospital').getQcCategory(session, cid=request.categoryId)
            qcItems = self.context.getQcItemRepository('hospital').getQcItemByIds(session, ids=request.itemsId)
            item_type_dict = {item.id: item.enableType for item in qcItems}
            category = rows[0] if rows and rows[0] else None
            if not category:
                return
            for itemId in request.itemsId:
                cateItem = {
                    'groupId': category.groupId,
                    'categoryId': category.id,
                    'itemId': itemId,
                    'maxScore': category.maxScore or 100,
                    'score': 1 if item_type_dict[itemId] == 1 else 0,
                }
                cateItem = QcCateItems.newObject(application.app, **cateItem)
                self.context.getQcItemRepository('hospital').add(session, cateItem)
        return g.result


class EditQcCategoryItem(MyResource):
    
    @pre_request(request, ["id:int", "score", "maxScore"])
    def post(self):
        """修改质控点设置
        """
        if not request.id:
            return get_error_resp("id can not be empty.")
        application = self.context.getCaseApplication("hospital")
        with application.app.mysqlConnection.session() as session:
            rows = self.context.getQcGroupRepository('hospital').getQcCateItems(session, qci=request.id)
            item = rows[0] if rows and rows[0] else None
            if item:
                item.score = request.score or 0
                item.maxScore = request.maxScore or 0
        return g.result


class RemoveQcCategoryItem(MyResource):

    @pre_request(request, ["data"])
    def post(self):
        """规则组删除质控点
        """
        application = self.context.getCaseApplication("hospital")
        with application.app.mysqlConnection.session() as session:
            self.context.getQcGroupRepository('hospital').deleteQcCateItemsById(session, request.data)
        return g.result


class GetEMRQcItems(MyResource):

    @pre_request(request, ["emrName", "requirement", "tag:int"])
    def get(self):
        """获取文书对应质控点列表
        """
        response = {"data": []}
        app = self.context.getCaseApplication('hospital')
        groupId = app.app.config.get('qc.group.active.active')
        params = ['requirement', 'tag']
        reqDict = {c: getattr(request, c) for c in params}
        tag_dict = {1: '强制', 2: '否决'}
        with app.app.mysqlConnection.session() as session:
            category_items = {row.itemId: row for row in
                              self.context.getQcGroupRepository('hospital').getQcCateItems(session, groupId=groupId)}
            emrNames = []
            if not request.emrName:
                for name in self.context.getQcGroupRepository("hospital").getQcItemsStandardName(session):
                    if name:
                        emrNames.append(name)
            else:
                emrNames.append(request.emrName)
            for emr in emrNames:
                data = {"items": {}}  # response.data.add()
                # {"items": []}
                data["docName"] = emr
                reqDict['emrName'] = emr
                req = GetItemsListRequest(**reqDict)
                items = self.context.getQcItemRepository('hospital').getList(session, req)
                doc_items_list = []
                for item in items:
                    if item.id not in category_items:
                        continue
                    else:
                        doc_items_list.append(item)
                doc_items_list.sort(key=lambda x: (x.cautionModel or ""), reverse=True)
                items = groupby(doc_items_list, key=lambda x: x.cautionModel)
                for name, group in items:
                    total = 0
                    if name:
                        data["items"][name] = {"items": []}
                        item = data["items"][name]
                    else:
                        data["items"]['无报警模块'] = {"items": []}
                        item = data["items"]['无报警模块']
                    for g in group:
                        total += 1
                        qc_item = {} # item.items.add()
                        qc_item["name"] = g.requirement
                        qc_item["tag"] = tag_dict.get(g.veto, '')
                        qc_item["warningModel"] = g.cautionModel or ""
                        qc_item["score"] = float(category_items.get(g.id).score)
                        qc_item["maxScore"] = float(category_items.get(g.id).maxScore)
                        item["items"].append(qc_item)
                    item["itemTotal"] = total
                data["total"] = len(doc_items_list)
                response["data"].append(data)
        return response


class RuleSearch(MyResource):

    @pre_request(request, RuleSearchReq)
    def post(self):
        """
        质控规则条件脑图查询
        :param request:
        :param context:
        :return:
        """
        response = {"items": []}
        app = self.context.getRuleApplication()
        data, response["total"] = app.queryKeywordsData(request)
        for item in data:
            response["items"].append(item)
        response["start"] = request.start or 0
        response["size"] = request.size or 10
        return response


class RuleSearchTypes(MyResource):

    def get(self):
        """
        质控规则条件脑图-类型查询
        :param request:
        :param context:
        :return:
        """
        response = {"items": []}
        app = self.context.getRuleApplication()
        data = app.queryKeywordsTypesData()
        for item in data:
            protoItem = {}  # response.items.add()
            protoItem["name"] = item
            response["items"].append(protoItem)
        return response


class RuleSearchTypesStats(MyResource):

    @pre_request(request, ["text"])
    def post(self):
        """
        质控规则条件脑图-关键字查分类
        :param request:
        :param context:
        :return:
        """
        response = {"items": []}
        app = self.context.getRuleApplication()
        data, response["total"] = app.queryKeywordsTypesStatsData(request)
        for name, count in data.items():
            protoItem = {}  # response.items.add()
            protoItem["name"] = name
            protoItem["value"] = float(count)
            response["items"].append(protoItem)
        return response














        



