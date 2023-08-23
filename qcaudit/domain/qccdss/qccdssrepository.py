from qc_document_classifier.contrast import DocTypeItem
from qc_document_classifier.special import SpecialRaw

from qcaudit.common.const import EMR_DOCUMENTS_REG
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.app import Application
from qcaudit.domain.qccdss.req import GetAuditInfoBaseRequest
from qcaudit.domain.case.emr import EmrDocument
from qcaudit.domain.lab.labreport import LabReport
from qcaudit.domain.case.exam import ExamReport
from qcaudit.domain.case.order import Order
from sqlalchemy import text
from qcaudit.domain.case.case import Case

from qcaudit.utils.document_classifier.classifier import Classifier


class QCCdssRepository(RepositoryBase):
    def __init__(self, app: Application):
        super().__init__(app, 'hospital')
        self.emrInfoModel = app.mysqlConnection['emrInfo']
        self.emrContentModel = app.mysqlConnection['emrContent']
        self.adviceModel = app.mysqlConnection['medicalAdvice']
        self.labInfoModel = app.mysqlConnection['labInfo']
        self.labContentModel = app.mysqlConnection['labContent']
        self.examInfoModel = app.mysqlConnection['examInfo']
        self.examContentModel = app.mysqlConnection['examContent']
        self.temperatureModel = app.mysqlConnection['temperature_form']
        self.mzdiagnosisModel = app.mysqlConnection['mz_diagnosis']
        self.fpdiagnosisModel = app.mysqlConnection['fpdiagnosis']
        self.fpoperationModel = app.mysqlConnection['fpoperation']
        self.pathologyModel = app.mysqlConnection['raw_data']
        self.documentsModel = app.mysqlConnection['documents']
        self.documentClassifyRegexp = app.mysqlConnection['document_classify_regexp']
        self.departmentModel = app.mysqlConnection['department']
        self.caseModel = app.mysqlConnection['case']
        # 标准文书对照分类器
        self._emrClassifier = self.initEmrClassifier()

    def initEmrClassifier(self):
        # 所有标准文书集合
        standard_types = [item[0] for item in EMR_DOCUMENTS_REG]
        # 标准文书正则规则
        doc_type_items = [DocTypeItem.parse_obj({'name': item[0], 'type': item[1], 'reg': item[2]}) for item in EMR_DOCUMENTS_REG]
        # 由医学部人工确认过的对照表
        mapping_data = []
        # 医院自定义正则规则
        regs_data = []
        with self.app.mysqlConnection.session() as session:
            for d in session.query(self.documentsModel).all():
                if d.standard_name not in standard_types:
                    continue
                mapping_data.append((d.name, d.standard_name))
            for dcr in session.query(self.documentClassifyRegexp).all():
                regs_data.append((dcr.regexp, dcr.standard_name))

        # 医生职称表，用于查找副主任查房和主治查房
        doctors_data = []
        # 创建实例
        special_raw = SpecialRaw(mapping=mapping_data, regs=regs_data, doctors=doctors_data)
        return Classifier(doc_type_items=doc_type_items, special_raw=special_raw)

    def getCaseDetail(self, session, caseId):
        item = session.query(self.caseModel).filter(self.caseModel.caseId == caseId).first()
        session.expunge(item)
        return Case(item)

    def getFirstPageInfo(self, session, caseId):
        model = self.app.mysqlConnection['firstpage']
        info = session.query(model).filter(model.caseId == caseId).first()
        if info:
            session.expunge(info)
            return info
        return None

    def getCaseEmr(self, session, req: GetAuditInfoBaseRequest):
        """获取文书列表
        Args:
            session ([type]): [description]
            req (GetEmrListRequest): [description]

        Returns:
            List[EmrDocument]: [description]
        """
        if req.withContent:
            query = session.query(self.emrInfoModel, self.emrContentModel).join(
                self.emrContentModel, self.emrInfoModel.emrContentId == self.emrContentModel.id, isouter=True
            ).order_by(self.emrInfoModel.createTime)
        else:
            query = session.query(self.emrInfoModel).order_by(self.emrInfoModel.recordTime)
        query = query.filter(self.emrInfoModel.caseId == req.caseId, self.emrInfoModel.is_deleted == 0)
        result = []
        for row in query.all():
            # 文书标准名称对照
            doc_types = []
            if self._emrClassifier and row[0] and row[0].documentName:
                doc_types = self._emrClassifier.get_full_types_by_title(row[0].documentName.strip())
            if not doc_types:
                doc_types = self._emrClassifier.get_full_types_by_title(row[0].originType.strip())
            if req.withContent:
                result.append(EmrDocument(row[0], row[1], doc_types=doc_types))
            else:
                result.append(EmrDocument(row, doc_types=doc_types))
        return result

    def getDoctorAdvice(self, session, req: GetAuditInfoBaseRequest):
        orders = []
        query = session.query(self.adviceModel).filter(self.adviceModel.caseId == req.caseId)
        for row in query.all():
            session.expunge(row)
            orders.append(Order(row))
        return orders

    def getLabList(self, session, req: GetAuditInfoBaseRequest):
        """
        获取化验数据
        """
        query = session.query(self.labInfoModel, self.labContentModel). \
            join(self.labContentModel, self.labInfoModel.id == self.labContentModel.reportId). \
            filter(self.labInfoModel.caseId == req.caseId, self.labContentModel.caseId == req.caseId). \
            filter(self.labInfoModel.is_deleted == 0). \
            order_by(self.labInfoModel.reportTime.is_(None), self.labInfoModel.reportTime.asc())
        result = []
        report_index = {}  # 记录reportId-index对照关系
        for row in query.all():
            if report_index.get(row[0].id) is None:
                result.append(LabReport(row[0], [row[1]]))
                report_index[row[0].id] = len(result) - 1
            else:
                result[report_index[row[0].id]].contents.append(row[1])
        return result

    def getExamList(self, session, req: GetAuditInfoBaseRequest):

        """
        获取检查数据
        """
        query = session.query(self.examInfoModel, self.examContentModel). \
            join(self.examContentModel, self.examInfoModel.id == self.examContentModel.reportId). \
            filter(self.examInfoModel.caseId == req.caseId, self.examContentModel.caseId == req.caseId). \
            filter(self.examInfoModel.is_deleted == 0). \
            order_by(self.examInfoModel.reportTime.is_(None), self.examInfoModel.reportTime.asc())
        result = []
        report_index = {}  # 记录reportId-index对照关系
        for row in query.all():
            if report_index.get(row[0].id) is None:
                result.append(ExamReport(row[0], [row[1]]))
                report_index[row[0].id] = len(result) - 1
            else:
                result[report_index[row[0].id]].contents.append(row[1])
        return result

    def getTemperatureInfo(self, session, req: GetAuditInfoBaseRequest):
        temperatureObjs = session.query(self.temperatureModel).filter(self.temperatureModel.caseId == req.caseId).all()
        result = []
        for obj in temperatureObjs:
            session.expunge(obj)
            result.append(obj)
        return result

    def getMZDiagnosisInfo(self, session, req: GetAuditInfoBaseRequest):
        """获取门诊诊断"""
        diagnosisObjs = session.query(self.mzdiagnosisModel).filter(
            self.mzdiagnosisModel.caseId == req.caseId).order_by(text('diagId+0 asc'))
        result = []
        for obj in diagnosisObjs:
            session.expunge(obj)
            result.append(obj)
        return result

    def getFpDiagnosisInfo(self, session, req: GetAuditInfoBaseRequest):
        fpdiagnosisObjs = session.query(self.fpdiagnosisModel).filter(
            self.fpdiagnosisModel.caseId == req.caseId).all()
        result = []
        for obj in fpdiagnosisObjs:
            session.expunge(obj)
            result.append(obj)
        return result

    def getFpOperationInfo(self, session, req: GetAuditInfoBaseRequest):
        fpoperationObjs = session.query(self.fpoperationModel).filter(
            self.fpoperationModel.caseId == req.caseId).all()
        result = []
        for obj in fpoperationObjs:
            session.expunge(obj)
            result.append(obj)
        return result

    def getPathologyInfo(self, session, req: GetAuditInfoBaseRequest):
        pathologyObjs = session.query(self.pathologyModel).filter(
            self.pathologyModel.caseId == req.caseId).all()
        result = []
        for obj in pathologyObjs:
            session.expunge(obj)
            result.append(obj)
        return result

    def getDepartmentDict(self, session):
        result = dict()
        items = session.query(self.departmentModel).all()
        for item in items:
            session.expunge(item)
            result[item.code] = item
        return result
