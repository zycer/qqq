from .basedata import AuditRecord, Branch, Case, CaseFee, EmrInfo, ExamInfo, EmrContent, ExamContent, ActiveRecord
from .basedata import Firstpage, FpOperation, FpDiagnosis, LabInfo, LabContent, MzCase, MzDiagnosis
from .basedata import MedicalAdvice, NormalDict, NonDrugOrderDict, Operation, Patient, RawData, TemperatureForm
from .basedata import Doctor, Departmentdict, WardDict
from .common import ConfigItem, EmrParserResult
from .disease import DiseaseDesc, DiseaseAuditor, DiseaseReporter, DiseaseItemDesc, ReasonConf, TimeOutConf
from .disease import DiseaseReportItem, CaseDisease, ReportTracelog, ScriptLog, FillItemsLog, PatientBaseInfo
from .fee import FeeMajor, FeeManager, FeeDiseaseMajor, FeeSingleDisease, FeeProject, FeeApplyForm
from .hospexpert import ExpertDept
from .hospqc import AuthStat
from .knowledge import Knowledge, KnowledgeCatalog, KnowledgeDetail, KnowledgeFile, KnowledgeType
from .qcaudit import AuditEmrInfo, MedicalAdviceType, CaseProblem, Calendar, CheckHistory, DocumentClassifyRegexp, \
    SampleOperation, SampleFilter, SampleTask, CaseProblemRecord
from .qcaudit import Document, WardDoctor, TagsQc, OrganDict, DiagnosisDict, OperationDict, Diagnosis, RefuseHistory
from .qcaudit import ExpertUser, Drugclass, Department, Tag
from .qcaudit import RefuseDetail, Ward, SampleRecordItem, SampleRecord, ScoreReportQcitem, ScoreReportTemplate
from .qcaudit import ExternalLink
from .qccdss import CdssMessage, CdssColorInfo, ExamPosition
from .qcdoctor import DoctorSetting, DoctorDebugLog, AppealInfo, IpRule
from .qcetl import MessageHistory, Dbinfo, EtlConfig, SyncTime, SyncError
from .qcevent import CaseEvent, DoctorActionLog
from .qcicd import CodingOperation, MiOperationDict, OperationOriginDict, DiagnosisOriginDict
from .qcicd import DiagnosisInfo, MiDiagnosisDict, OperationInfo, FpInfo, Narcosi
from .qcitem import QcItem, QcGroup, QcCateItem, QcCategory
from .ruleengine import RuleQuery, RuleScene, RuleSystem, RuleDetail, RuleBindScene, QcItemRule, QcKeyword, Keyword


QCAUDIT_TABLES = [
    Branch, Department, Departmentdict, Doctor, Ward, WardDoctor, WardDict, Calendar, Diagnosis, DiagnosisDict,
    OperationDict, MedicalAdviceType, QcItem, QcGroup, QcCategory, Drugclass, Tag, TagsQc, QcItemRule, QcKeyword,
    AuditRecord, Case, EmrInfo, EmrContent, MedicalAdvice, ExamInfo, ExamContent, ExamPosition, LabInfo, LabContent,
    Firstpage, FpDiagnosis, FpOperation, MzDiagnosis, Operation, TemperatureForm, RawData,
    Document, DocumentClassifyRegexp, AuditEmrInfo, CaseProblem, CheckHistory, RefuseHistory, RefuseDetail,
    ExpertUser, SampleRecord, SampleRecordItem, SampleOperation,
    QcCateItem, ScoreReportTemplate, ScoreReportQcitem,
    AppealInfo, IpRule, DoctorDebugLog,
    ConfigItem, EmrParserResult,
    CaseEvent, DoctorActionLog,
    RuleQuery, RuleScene, RuleSystem, RuleDetail, RuleBindScene, QcItemRule, QcKeyword, Keyword,
    CdssMessage, CdssColorInfo,
    Knowledge, KnowledgeCatalog, KnowledgeDetail, KnowledgeFile, KnowledgeType,
    MessageHistory, Dbinfo, EtlConfig, SyncTime, SyncError, DoctorSetting,
    CaseDisease, ReportTracelog,
    ExternalLink, ActiveRecord, SampleFilter, SampleTask, CaseProblemRecord,
    NormalDict, 
    # 编码
    DiagnosisInfo, DiagnosisOriginDict, FpInfo, MiDiagnosisDict, MiOperationDict, Narcosi, 
    OperationInfo, OperationOriginDict, CodingOperation
]
