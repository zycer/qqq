from flask_restful import Api
from qcaudit.controller.qc_handler import *
from qcaudit.controller.sample_handler import *
from qcaudit.controller.doctor_handler import *
from qcaudit.controller.qcItem_handler import *
from qcaudit.controller.stats_handler import *
from qcaudit.controller.qcevent_handler import *
from qcaudit.controller.qccdss_handler import *
from qcaudit.controller.firstpage_handler import *


prefix = '/hosp/qc/v3'


def init_url_route(app):
    """
        初始化所有的路由和hanlder关系
    :param app:
    :return:
    """
    api = Api(app)
    # qcaudit
    api.add_resource(GetBranch, prefix + '/branch')
    api.add_resource(GetWard, prefix + '/ward')
    api.add_resource(GetDepartment, prefix + '/department')
    api.add_resource(AddDepartment, prefix + '/department/add')
    api.add_resource(GetCaseTag, prefix + '/dict/tags')
    api.add_resource(GetAuditStatus, prefix + '/dict/status')
    api.add_resource(GetDoctors, prefix + '/doctors')
    api.add_resource(GetReviewers, prefix + '/reviewer')
    api.add_resource(GetStandardEmr, prefix + '/standard/emr')
    api.add_resource(GetCaseQcItems, prefix + '/item/list/<string:caseId>')
    api.add_resource(GetCaseList, prefix + '/case/list')
    api.add_resource(CaseExport, prefix + '/case/export')
    api.add_resource(DownloadFile, prefix + '/export/download')
    api.add_resource(GetInpatientList, prefix + '/inpatient/list')
    api.add_resource(GetCaseTimeline, prefix + '/case/timeline')
    api.add_resource(GetRefusedProblem, prefix + '/audit/problem/refused')
    api.add_resource(GetCaseDetail, prefix + '/case/detail')
    api.add_resource(GetCaseEmrList, prefix + '/case/emr/list')
    api.add_resource(GetEmrVersion, prefix + '/case/emr/version')
    api.add_resource(GetEmrDiff, prefix + '/case/emr/diff')
    api.add_resource(GetCaseEmr, prefix + '/case/emr')
    api.add_resource(GetCaseProblem, prefix + '/case/problem')
    api.add_resource(CheckProblem, prefix + '/check/problem')
    api.add_resource(CheckEmr, prefix + '/check/emr')
    api.add_resource(AddCaseProblem, prefix + '/case/problem')
    api.add_resource(AddQCItemProblem, prefix + '/item/add')
    api.add_resource(UpdateCaseProblem, prefix + '/case/update/problem')
    api.add_resource(DeductProblem, prefix + '/case/problem/deduct/<string:id>')
    api.add_resource(DeleteCaseProblem, prefix + '/case/problem/<string:id>')
    api.add_resource(GetCaseDoctors, prefix + '/case/doctors')
    api.add_resource(SetRefuseDoctor, prefix + '/case/set/refuseDoctor')
    api.add_resource(BatchSetRefuseDoctor, prefix + '/case/batchset/refuseDoctor')
    api.add_resource(GetRefuseDoctor, prefix + '/case/get/refuseDoctor')
    api.add_resource(GetCaseReason, prefix + '/case/reasons')
    api.add_resource(ApproveCase, prefix + '/case/approved')
    api.add_resource(ApproveCaseBatch, prefix + '/case/approve/batch')
    api.add_resource(RefuseCase, prefix + '/case/refused')
    api.add_resource(AddRefuseCase, prefix + '/case/add/refused')
    api.add_resource(LockCase, prefix + '/case/lock')
    api.add_resource(UnlockCase, prefix + '/case/unlock')
    api.add_resource(RevokeApproved, prefix + '/case/revoke/approved')
    api.add_resource(RevokeRefused, prefix + '/case/revoke/refused')
    api.add_resource(GetCaseCheckHistory, prefix + '/case/check/history/<string:caseId>')
    api.add_resource(GetAdviceType, prefix + '/adviceType')
    api.add_resource(GetMedicalAdvice, prefix + '/medicalAdvice')
    api.add_resource(GetEmrData, prefix + '/emrdata')
    api.add_resource(GetConfigItems, prefix + '/config/items')
    api.add_resource(CrawlCase, prefix + '/crawl/case')
    api.add_resource(GetCaseDeductDetail, prefix + '/archive/deduct/detail')
    api.add_resource(ArchiveScoreExport, prefix + '/archive/case/export')
    api.add_resource(GetDiseaseList, prefix + '/dict/disease')
    api.add_resource(GetDiagnosisList, prefix + '/dict/diagnosis')
    api.add_resource(GetOperationList, prefix + '/dict/operation')
    api.add_resource(GetOrg, prefix + '/dict/organ')
    api.add_resource(GetCalendar, prefix + '/calendar/get')
    api.add_resource(SetCalendar, prefix + '/calendar/set')
    api.add_resource(GetQCReport, prefix + '/report')
    api.add_resource(GetCaseLab, prefix + '/case/lab')
    api.add_resource(GetCaseExam, prefix + '/case/exam')
    api.add_resource(GetIpBlockList, prefix + '/ip/block')
    api.add_resource(DeleteIpBlock, prefix + 'ip/block/<int:id>')
    api.add_resource(GetConfigList, prefix + '/config/list')
    api.add_resource(UpdateConfigList, prefix + '/config/update')
    api.add_resource(CaseGroupList, prefix + '/case/group')
    api.add_resource(ArchiveSampleList, prefix + '/archive/sample')
    api.add_resource(ExternalSystemLinks, prefix + '/external/links')
    api.add_resource(ActiveSave, prefix + '/active/save')
    api.add_resource(ProblemRecordList, prefix + '/problem/record/list')
    api.add_resource(ProblemRecordDetail, prefix + '/problem/record/detail')
    api.add_resource(UrgeRefusedCase, prefix + '/urge/case')
    # sample
    api.add_resource(GetSampleCase, prefix + '/sample/case/list')
    api.add_resource(SubmitSampleCase, prefix + '/sample/case/submit')
    api.add_resource(GetSampleList, prefix + '/sample/list')
    api.add_resource(GetSampleDetail, prefix + '/sample/case/detail')
    api.add_resource(GetSampleDetailExport, prefix + '/sample/case/detail/export')
    api.add_resource(AssignSample, prefix + '/sample/assign/sample')
    api.add_resource(AssignTask, prefix + '/sample/assign/task')
    api.add_resource(DeleteTask, prefix + '/sample/task/delete')
    api.add_resource(GetExpertList, prefix + '/sample/expert/list')
    api.add_resource(AddExpert, prefix + '/sample/expert/add')
    api.add_resource(DeleteExpert, prefix + '/sample/expert/delete')
    api.add_resource(BranchAssignTask, prefix + '/sample/branch/assign')
    api.add_resource(BranchAssignDoctorList, prefix + '/sample/branch/doctor/list')
    api.add_resource(UpdateSampleCase, prefix + '/sample/case/update')
    api.add_resource(GetSampleOperation, prefix + '/sample/operations')
    api.add_resource(SampleFilterList, prefix + '/sample/filter/list')
    api.add_resource(SampleFilterSave, prefix + '/sample/filter/save')
    api.add_resource(SampleTaskList, prefix + '/sample/task/list')
    api.add_resource(SampleTaskSave, prefix + '/sample/task/save')
    # doctor 
    api.add_resource(GetDoctorIsRemind, prefix + '/doctor/isRemind')
    api.add_resource(UpdateDoctorNotRemind, prefix + '/doctor/notRemind')
    api.add_resource(GetDoctorRefuseCaseNum, prefix + '/doctor/refuseCase/num')
    api.add_resource(GetDoctorRefuseCaseList, prefix + '/doctor/case/todoList')
    api.add_resource(UpdateCaseIsRead, prefix + '/doctor/update/isRead')
    api.add_resource(GetDoctorEMRProblemNum, prefix + '/doctor/emr/problem/num')
    api.add_resource(GetDoctorEMRProblemList, prefix + '/doctor/emr/problem/list')
    api.add_resource(GetDoctorEMRExtractProblemList, prefix + '/doctor/emr/extract/problem/list')
    api.add_resource(GetDoctorEMRAuditRecordList, prefix + '/doctor/emr/audit/record')
    api.add_resource(UpdateProblemFixFlag, prefix + '/doctor/problem/fix/update')
    api.add_resource(ProblemAppeal, prefix + '/doctor/matter/problem/appeal')
    api.add_resource(ProblemIgnore, prefix + '/doctor/problem/ignore')
    api.add_resource(GetEMRCaseSubmitApplyList, prefix + '/doctor/emr/case/submit/apply/list')
    api.add_resource(EMRCaseSubmit, prefix + '/doctor/emr/case/submit')
    api.add_resource(EMRCaseTransfer, prefix + '/doctor/emr/case/transfer')
    api.add_resource(EMRDocSave, prefix + '/doctor/emr/doc/save')
    api.add_resource(EMRDocPartSave, prefix + '/doctor/emr/doc/partSave')
    api.add_resource(EMRDocDelete, prefix + '/doctor/emr/doc/delete')
    api.add_resource(GetCaseStatus, prefix + '/doctor/case/status')
    api.add_resource(GetAppealNotReadCount, prefix + '/appeal/count')
    api.add_resource(GetAppealNotReadCaseList, prefix + '/appeal/case/list')
    api.add_resource(GetCaseAppealProblemList, prefix + '/appeal/problem/list')
    api.add_resource(GetCaseAppealDetail, prefix + '/appeal/detail')
    api.add_resource(AppealCreate, prefix + '/appeal/create')
    api.add_resource(AppealDelete, prefix + '/appeal/delete')
    api.add_resource(AppealProblemIsRead, prefix + '/appeal/problem/read')
    api.add_resource(AppealModify, prefix + '/appeal/modify')
    api.add_resource(MessageReceive, prefix + '/message/receive')
    # api.add_resource(EmrSaveDebug, prefix + '/doctor/debug')  # AssertionError: Unimplemented method ''
    api.add_resource(GetIpPlan, prefix + '/doctor/plan')
    api.add_resource(ApplyArchive, prefix + '/doctor/apply/archive')
    api.add_resource(TryCancelApplyArchive, prefix + '/doctor/cancel/apply')
    # qcItem
    api.add_resource(CreateQCItem, prefix + '/item/create')
    api.add_resource(UpdateQCItem, prefix + '/item/update')
    api.add_resource(EnableQCItem, prefix + '/item/enable')
    api.add_resource(DeleteQCItem, prefix + '/item/<int:id>')
    api.add_resource(GetQCItem, prefix + '/items/<int:id>')
    api.add_resource(ListQCItem, prefix + '/item/list')
    api.add_resource(ApproveQCItem, prefix + '/items/approve')
    api.add_resource(DeleteQCItems, prefix + '/items/delete')
    api.add_resource(ExportQCItems, prefix + '/items/export')
    api.add_resource(GetQcGroup, prefix + '/qcgroup')
    api.add_resource(GetQcGroupItem, prefix + '/qcgroup/item')
    api.add_resource(GetQcCategory, prefix + '/qcgroup/category')
    api.add_resource(EditQcCategory, prefix + '/qcgroup/category/<int:id>')
    api.add_resource(AddQcCategoryItem, prefix + '/qccategory/item/add')
    api.add_resource(EditQcCategoryItem, prefix + '/qccategory/item/edit')
    api.add_resource(RemoveQcCategoryItem, prefix + '/qccategory/item/remove')
    api.add_resource(GetEMRQcItems, prefix + '/emr/items')
    api.add_resource(RuleSearch, prefix + '/item/keyword/search')
    api.add_resource(RuleSearchTypes, prefix + '/item/keyword/types')
    api.add_resource(RuleSearchTypesStats, prefix + '/item/keyword/types/stats')
    # stats
    api.add_resource(StatsCaseRatio, prefix + '/stats/case/ratio')
    api.add_resource(StatsDepartmentScore, prefix + '/stats/department/score')
    api.add_resource(StatsCaseTarget, prefix + '/stats/case/target')
    api.add_resource(StatsCaseDefectRate, prefix + '/stats/case/defect/rate')
    api.add_resource(StatsCaseDefectCount, prefix + '/stats/case/defect/count')
    api.add_resource(StatsFlagCaseDefectList, prefix + '/stats/case/flag/defect/list')
    api.add_resource(GetStatsDataUpdateStatus, prefix + '/stats/data/update/status')
    api.add_resource(StatsDataUpdate, prefix + '/stats/data/update')
    api.add_resource(GetStatsTableUpdateStatus, prefix + '/stats/table/update/status')
    api.add_resource(StatsTableUpdate, prefix + '/stats/table/update')
    api.add_resource(GetHospitalArchivingRate, prefix + '/stats/archivingrate/hospital')
    api.add_resource(GetDepartmentArchivingRate, prefix + '/stats/archivingrate/department')
    api.add_resource(ExportDepartmentArchivingRate, prefix + '/stats/archivingrate/department/export')
    api.add_resource(GetMonthArchivingRate, prefix + '/stats/archivingrate/month')
    api.add_resource(GetBranchTimelinessRate, prefix + '/stats/timeliness/branch')
    api.add_resource(GetBranchTimelinessRateExport, prefix + '/stats/timeliness/branch/export')
    api.add_resource(GetBranchTimelinessRateDetail, prefix + '/stats/timeliness/branch/detail')
    api.add_resource(GetBranchTimelinessRateDetailFormula, prefix + '/stats/timeliness/branch/detail/formula')
    api.add_resource(GetBranchTimelinessRateDetailExport, prefix + '/stats/timeliness/branch/detail/export')
    api.add_resource(GetDoctorArchivingRate, prefix + '/stats/archivingrate/doctor')
    api.add_resource(ExportDoctorArchivingRate, prefix + '/stats/archivingrate/export')
    api.add_resource(GetDirectorArchivingRate, prefix + '/stats/archivingrate/director')
    api.add_resource(GetDoctorArchivingRateCase, prefix + '/stats/archivingrate/doctor/case')
    api.add_resource(ExportDoctorArchivingRateCase, prefix + '/stats/archivingrate/case/export')
    api.add_resource(ExportDirectorArchivingRateCase, prefix + '/stats/archivingrate/director/case/export')
    api.add_resource(ExportDirectorArchivingRate, prefix + '/stats/archivingrate/director/export')
    api.add_resource(GetMedicalIndicatorStats, prefix + '/stats/medical/indicator')
    api.add_resource(ExportMedicalIndicatorStats, prefix + '/stats/medical/indicator/export')
    api.add_resource(GetMedicalIndicatorStatsCase, prefix + '/stats/medical/indicator/case')
    api.add_resource(ExportMedicalIndicatorStatsCase, prefix + '/stats/medical/indicator/export/case')
    api.add_resource(GetStatsCaseTag, prefix + '/stats/dict/tags')
    api.add_resource(GetFirstPageProblems, prefix + '/stats/firstpage/problems')
    api.add_resource(GetFirstPageScoreStats, prefix + '/stats/firstpage/score')
    api.add_resource(GetFirstPageScoreDistribution, prefix + '/stats/firstpage/score/distribution')
    api.add_resource(GetFirstPageIndicateStats, prefix + '/stats/firstpage/indicator/stats')
    api.add_resource(GetFirstPageProblemConfig, prefix + '/stats/firstpage/problem/config')
    api.add_resource(ModifyFirstPageProblemConfig, prefix + '/stats/firstpage/problem/config/modify')
    api.add_resource(GetBatchFirstPageIndicateStats, prefix + '/stats/firstpage/indicator/stats/batch')
    api.add_resource(GetProblemCategoryStats, prefix + '/stats/problem/category')
    api.add_resource(GetCaseByProblem, prefix + '/stats/problem/case')
    api.add_resource(ExportProblemCateStats, prefix + '/stats/problem/export')
    api.add_resource(ExpertAllNum, prefix + '/stats/expert/all/num')
    api.add_resource(ExpertAllLevel, prefix + '/stats/expert/all/level')
    api.add_resource(ExpertAllScorePic, prefix + '/stats/expert/all/score/pic')
    api.add_resource(ExpertAllDetail, prefix + '/stats/expert/all/score')
    api.add_resource(ExpertAllDetailExport, prefix + '/stats/expert/all/score/export')
    api.add_resource(ExpertDeptScorePic, prefix + '/stats/expert/dept/score/pic')
    api.add_resource(ExpertDeptScoreLevel, prefix + '/stats/expert/dept/score/level')
    api.add_resource(ExpertDeptScoreList, prefix + '/stats/expert/dept/score/list')
    api.add_resource(ExpertDeptScoreDetail, prefix + '/stats/expert/dept/score/detail')
    api.add_resource(ExpertDeptScoreDetailExport, prefix + '/stats/expert/dept/score/export')
    api.add_resource(ExpertDoctorScore, prefix + '/stats/expert/doctor/score')
    api.add_resource(ExpertDoctorScoreExport, prefix + '/stats/expert/doctor/score/export')
    api.add_resource(GetUpdateTime, prefix + '/stats/update/time')
    api.add_resource(StatsDefectRateList, prefix + '/stats/defect/rate/list')
    api.add_resource(StatsDefectRateExport, prefix + '/stats/defect/rate/export')
    api.add_resource(StatsDefectRateDetailList, prefix + '/stats/defect/rate/detail/list')
    api.add_resource(StatsDefectRateDetailExport, prefix + '/stats/defect/rate/detail/export')
    api.add_resource(StatsDefectRateUpdateStatus, prefix + '/stats/defect/rate/update/status')
    api.add_resource(StatsDefectRateUpdate, prefix + '/stats/defect/rate/update')
    api.add_resource(StatsArchivedQualityList, prefix + '/stats/archived/quality/list')
    api.add_resource(StatsArchivedQualityExport, prefix + '/stats/archived/quality/export')
    api.add_resource(StatsArchivedQualityDetailList, prefix + '/stats/archived/quality/detail/list')
    api.add_resource(StatsArchivedQualityDetailExport, prefix + '/stats/archived/quality/detail/export')
    api.add_resource(StatsArchivedQualityUpdateStatus, prefix + '/stats/archived/quality/update/status')
    api.add_resource(StatsArchivedQualityUpdate, prefix + '/stats/archived/quality/update')
    api.add_resource(StatsRunningCaseNum, prefix + '/stats/running/case/num')
    api.add_resource(StatsRunningDeptTop, prefix + '/stats/running/dept/top')
    api.add_resource(StatsRunningDeptInfo, prefix + '/stats/running/dept/info')
    api.add_resource(StatsRunningType, prefix + '/stats/running/type')
    api.add_resource(StatsRunningTypeInfo, prefix + '/stats/running/type/info')
    api.add_resource(StatsVetoBaseInfo, prefix + '/stats/veto/base/info')
    api.add_resource(StatsVetoCaseTrendInfo, prefix + '/stats/veto/caseTrend/info')
    api.add_resource(StatsVetoDeptTopInfo, prefix + '/stats/veto/deptTop/info')
    api.add_resource(StatsVetoDoctorTopInfo, prefix + '/stats/veto/doctorTop/info')
    api.add_resource(StatsVetoProblemTypeInfo, prefix + '/stats/veto/problemType/info')
    api.add_resource(StatsVetoProblemNumInfo, prefix + '/stats/veto/problemNum/info')
    api.add_resource(StatsRefuseCaseNumInfo, prefix + '/stats/refuse/caseNum/info')
    api.add_resource(StatsRefuseRatioInfo, prefix + '/stats/refuse/ratio/info')
    api.add_resource(StatsRefuseDeptTopInfo, prefix + '/stats/refuse/deptTop/info')
    api.add_resource(StatsRefuseDoctorTopInfo, prefix + '/stats/refuse/doctorTop/info')
    api.add_resource(StatsRefuseProblemTypeInfo, prefix + '/stats/refuse/problemType/info')
    api.add_resource(StatsRefuseProblemNumInfo, prefix + '/stats/refuse/problemNum/info')
    api.add_resource(StatsArchiveCaseNumInfo, prefix + '/stats/archive/caseNum/info')
    api.add_resource(StatsArchiveRatioInfo, prefix + '/stats/archive/ratio/info')
    api.add_resource(StatsArchiveDeptTopInfo, prefix + '/stats/archive/deptTop/info')
    api.add_resource(StatsArchiveDoctorTopInfo, prefix + '/stats/archive/doctorTop/info')
    api.add_resource(StatsArchiveProblemNumTopInfo, prefix + '/stats/archive/numTop/info')
    api.add_resource(StatsArchiveProblemNumDoctorTopInfo, prefix + '/stats/archive/numDoctorTop/info')
    api.add_resource(StatsArchiveProblemTypeInfo, prefix + '/stats/archive/problemType/info')
    api.add_resource(StatsArchiveProblemNumInfo, prefix + '/stats/archive/problemNum/info')
    api.add_resource(GetWorkloadReport, prefix + '/stats/report/workload')
    api.add_resource(ExportWorkloadReport, prefix + '/stats/report/workload/export')
    # qcevent
    api.add_resource(ReceiveEvent, '/hosp/qc/event')
    api.add_resource(ReceiveActionEvent, '/hosp/qc/event/v2/action', '/hosp/qc/event/v3/action')
    api.add_resource(ReceiveDataHZh, '/hosp/qc/event/huzhou/upload')
    # qccdss
    api.add_resource(GetCaseLabExamInfo, prefix + '/case/lab/exam/info')
    api.add_resource(GetPatientPortrait, prefix + '/stats/analyze/patient')
    api.add_resource(GetDoctorCaseList, prefix + '/doctor/case/list')
    api.add_resource(GetQcAuditDataByCaseId, prefix + '/audit/data')
    api.add_resource(GetParserResult, prefix + '/parser/data')
    # firstpage
    api.add_resource(GetList, prefix + '/firstpage/list')
    api.add_resource(GetListExport, prefix + '/firstpage/list/export')
    api.add_resource(GetCaseDiagnosis, prefix + '/firstpage/case/diagnosis/list')
    api.add_resource(GetDiagnosis, prefix + '/firstpage/diagnosis/list')
    api.add_resource(SaveCaseDiagnosis, prefix + '/firstpage/case/diagnosis/save')
    api.add_resource(DeleteCaseDiagnosis, prefix + '/firstpage/case/diagnosis/delete')
    api.add_resource(GetCaseOperation, prefix + '/firstpage/case/operation/list')
    api.add_resource(GetOperation, prefix + '/firstpage/operation/list')
    api.add_resource(SaveCaseOperation, prefix + '/firstpage/case/operation/save')
    api.add_resource(DeleteCaseOperation, prefix + '/firstpage/case/operation/delete')
    api.add_resource(GetNarcosis, prefix + '/firstpage/narcosis/list')
    api.add_resource(SubmitCheck, prefix + '/firstpage/case/submit/check')
    api.add_resource(Submit, prefix + '/firstpage/case/submit')
    api.add_resource(CaseDetail, prefix + '/firstpage/case/detail')
    # api.add_resource(DownloadFile, prefix + '/firstpage/export/download')












