from dataclasses import replace
import json
from pathlib import Path

from .beam_register import service as intake_service
from .curing_windows import service as cohort_service
from .maturity_signals import service as feature_service
from .strength_classifier import service as model_service
from .cube_validation import service as calibration_service
from .recipe_shift import service as monitor_service
from .retest_press import service as dispatch_service
from .casting_release import service as audit_service
from .curing_windows import contracts as window_contract

PRESET = Path(__file__).resolve().parents[2] / 'sample_data' / 'beam_register_sample.json'
MODULES = (('beam_register', '梁批登记'),
 ('curing_windows', '养护分窗'),
 ('maturity_signals', '成熟度特征'),
 ('strength_classifier', '强度分类'),
 ('cube_validation', '试块核验'),
 ('recipe_shift', '配比变化'),
 ('retest_press', '压机复检'),
 ('casting_release', '拆模凭证'))
DISPLAY = {'title': '预制梁试块复核',
 'object_name': '预制梁批',
 'unit': '概率',
 'role': '构件厂试验员',
 'endpoint': 'beamcure',
 'identity': 'CURE / QA',
 'location': '构件二厂 · 蒸养质检室',
 'visual': '保温组风险对照',
 'queue': '试块复压批次',
 'resource': '压力机工位',
 'action': '安排试块复压',
 'lane': 'L2',
 'field_title': '试块见证排组'}


def open_fixture(path=PRESET):
    document = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or not isinstance(document.get('records'), list):
        raise ValueError('样例必须包含 records 数组')
    if len(document['records']) > 2500:
        raise ValueError('单次导入最多处理 2500 条单据')
    return document


def stage_at(index, details, records, issues=()):
    code, title = MODULES[index]
    return {'key': code, 'title': title, 'summary': details, 'records': list(records), 'errors': list(issues)}


def rows_for(plan, scored, vectors):
    by_key = {item.key: item for item in scored}
    factor_names = ('有效温时积', '胶材水负荷', '单位龄期梯度', '等效胶材量', '龄期温时代理')
    order = []
    for job in plan.jobs:
        point = by_key[job.key]
        if len(point.contributions) == len(factor_names):
            reasons = sorted(zip(factor_names, point.contributions, strict=True), key=lambda val: (-abs(val[1]), val[0]))
            driver = ' · '.join(f'{key} {amount:+.2f}' for key, amount in reasons[:2])
        else:
            driver = ' · '.join(f'{amount:+.2f}' for amount in point.contributions)
        interval = ('–' if job.lower is None else f'{job.lower:.2f}–{job.upper:.2f}')
        order.append({'key': job.key, 'zone': job.cohort, 'estimate': job.estimate, 'interval': interval,
                      'state': job.state, 'cost': job.cost, 'reason': job.reason, 'evidence': job.summary,
                      'drivers': driver, 'missing': len(point.missing), 'hits': list(job.rule_hits),
                      'measurements': dict(zip(('cure_min', 'chamber_c', 'binder_kg', 'water_pct', 'probe_gap', 'age_hours'), point.input_values, strict=True)),
                      'unmeasured': list(point.missing), 'operations': feature_service.business_factors(vectors[job.key])})
    return order


def comparison_rows(predictions):
    return [{'单号': point.key, '分组': point.cohort, '原始估计': round(point.score, 4),
             '补值字段': len(point.missing), '偏离特征': '、'.join(point.excursions) or '—'}
            for point in predictions[:14]]


def replay_metrics(report):
    result = [{'label': '回放实绩样本', 'value': report.count}, {'label': '回放绝对误差', 'value': report.mae}]
    return result


class ShiftDossier:
    def __init__(self, request, as_of):
        self.raw_forms = request
        self.calendar = replace(window_contract.WindowRule.standard(allow_censor=False),as_of=as_of)
        self.accepted = intake_service.load_samples(request,as_of)
        self.history = cohort_service.build_windows(self.accepted.entries,self.calendar)
        cohort_service.model_inputs(self.history)
        self.feature_stamp = feature_service.fit_features(self.history.train)
        self.prepared = feature_service.transform_windows(self.history,self.feature_stamp)
        self.forecaster = model_service.fit_model(self.prepared.train,self.feature_stamp.fingerprint)

    def grading(self):
        predictions = {}
        for name, points in self.prepared.segments():
            if name != 'train':
                predictions[name] = model_service.predict(self.forecaster,points,self.feature_stamp.fingerprint)
        checked = calibration_service.prepare_verification(predictions['calibration'])
        return checked, predictions

    def verification(self, observed, calibration):
        holdout = calibration_service.validate_predictions(observed['replay'],calibration)
        assignment = calibration_service.validate_predictions(observed['live'],calibration)
        prepared = self.prepared
        baseline = monitor_service.fit_baseline(prepared.train,self.feature_stamp.fingerprint)
        detection = monitor_service.scan_current(baseline,prepared.live,self.feature_stamp.fingerprint)
        return holdout, assignment, detection

    def seal(self, plan, mode):
        return audit_service.close_batch(self.raw_forms,self.accepted,self.history,plan,self.feature_stamp.fingerprint,self.forecaster.name,mode)


def execute(documents, capacity=12, mode='balanced', *, as_of=96):
    if type(as_of) is not int or as_of not in range(91,3651):
        raise ValueError('截至工日超出当前排班表')
    if not isinstance(documents,(tuple,list)) or not 1<=len(documents)<=2500:
        raise ValueError('需要 1 至 2500 份可识别单据')
    dossier = ShiftDossier(documents,as_of)
    fitted_calibration, estimates = dossier.grading()
    evaluated, checked_live, drift = dossier.verification(estimates,fitted_calibration)
    allocation = dispatch_service.plan_jobs(checked_live,drift.domain,capacity,mode)
    closed = dossier.seal(allocation,mode)
    intake,windows,state,features,kernel = dossier.accepted,dossier.history,dossier.feature_stamp,dossier.prepared,dossier.forecaster
    scored = estimates['live']
    performance = calibration_service.performance(evaluated)
    coverage = monitor_service.coverage_by_group(features.calibration,features.live)
    states = dict(closed.totals.states)
    overview = [
        {'label': '当班预制梁批', 'value': len(allocation.jobs)},
        {'label': '已分派', 'value': states.get('已分派', 0)},
        {'label': '候补', 'value': states.get('候补', 0)},
        {'label': '暂停及人工判读', 'value': states.get('暂停', 0) + states.get('人工判读', 0)},
        {'label': '额度结余', 'value': allocation.balance},
    ]
    vectors = {item.key: item for item in features.live}
    row_list = rows_for(allocation, scored, vectors)
    operating_rows = dispatch_service.operating_ledger(row_list)
    overtime = calibration_service.boundary_diagnostics(evaluated, 0.49)
    sector = calibration_service.sector_replay(evaluated, 0.49)
    operating_shift = monitor_service.shop_floor_shift(features.train, features.live)
    field_evidence = audit_service.sign_field_evidence(row_list, allocation)
    features_glance = feature_service.feature_evidence(state) + feature_service.measure_review(features)
    weight_rows = [{'量测': key, '取值': value} for key, value in kernel.evidence]
    ignored = [issue.evidence() for issue in intake.issues]
    details = [
        stage_at(0, f'接收 {intake.source_rows} 条，采用 {len(intake.entries)} 条', intake_service.preliminary_evidence(intake), ignored),
        stage_at(1, f'拟合 {len(windows.train)} 条，校准 {len(windows.calibration)} 条，回放 {len(windows.replay)} 条', cohort_service.window_evidence(windows) + cohort_service.readiness_evidence(windows, as_of)),
        stage_at(2, '特征转换版本 ' + state.fingerprint, features_glance),
        stage_at(3, kernel.name, weight_rows + model_service.inspection_rows(kernel, features) + comparison_rows(scored)),
        stage_at(4, f'{fitted_calibration.method} · {performance.status} · {performance.count} 条回放实绩', calibration_service.calibration_evidence(performance) + [overtime] + sector),
        stage_at(5, f'{drift.status} · {len(drift.domain)} 张单据需外推判读', monitor_service.shift_evidence(drift, coverage) + operating_shift),
        stage_at(6, f'本班占用 {allocation.capacity-allocation.balance} / {allocation.capacity} 个工位单位', dispatch_service.action_evidence(allocation) + dispatch_service.operating_group(checked_live, allocation)),
        stage_at(7, f'处置凭证 {closed.stamp} · 额度守恒', audit_service.reconciliation_evidence(closed) + field_evidence['执行业务单']),
    ]
    details[6]['operating_rows'] = operating_rows
    details[6]['operating_title'] = '试块见证排组'
    points = [{'label': row['key'], 'value': row['estimate'], 'state': row['state'], 'zone': row['zone'],
               'upper': row['interval'], 'cost': row['cost']} for row in sorted(row_list, key=lambda row: row['key'])]
    def estimate(vector):
        return calibration_service.check_point(model_service.predict_one(kernel, vector), fitted_calibration).estimate

    # Compare interventions against frozen features, model and calibration;
    # scenario estimates never overwrite the base ticket or its decision.
    for row in row_list:
        current = vectors[row['key']]
        row['alternatives'] = feature_service.render_interventions(current, state, estimate)
        row['joint_experiments'] = feature_service.render_joint_experiments(current,state,estimate)
    details[7]['records'].extend(audit_service.site_checklist(row_list))
    details[7]['records'].extend(audit_service.intervention_summary(row_list))
    overview_report = {'capacity' : capacity, 'mode': mode, 'as_of': as_of, 'sample_hash': closed.batch_hash,
              'policy_hash': closed.policy_hash, 'feature_stamp': state.fingerprint,
              'model': kernel.name, 'run_id': closed.stamp, 'object_name': DISPLAY['object_name'],
              'unit': DISPLAY['unit'], 'sections': details, 'flow_counts': list(states.items()),
              'measures': {'cure_min': ('有效保温', 'min'),
 'chamber_c': ('蒸养峰温', '℃'),
 'binder_kg': ('胶凝料用量', 'kg/m³'),
 'water_pct': ('水胶质量比', '%'),
 'probe_gap': ('两探头温差', '℃'),
 'age_hours': ('脱模前龄期', 'h')}, 'metrics': overview, 'performance': replay_metrics(performance), 'rows': row_list, 'series': points}
    return overview_report


def preview(capacity=12, mode='balanced'):
    fixture = open_fixture()
    return execute(fixture['records'], capacity, mode, as_of=fixture['as_of'])
