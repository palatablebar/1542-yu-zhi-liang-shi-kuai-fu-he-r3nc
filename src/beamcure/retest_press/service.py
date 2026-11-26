from .operating_ledger import operating_ledger
from collections import Counter, defaultdict
from math import exp, isfinite

from .contracts import RuleNotice, Job, Plan, Policy, RISK_CUTOFF
from .constraints import WorkOrder, apply_retest_press


def measures(raw):
    return tuple(raw)


def signals(data, estimate, missing=()):
    absent=frozenset(missing)
    cure_min, chamber_c, binder_kg, water_pct, probe_gap, age_hours = data
    hits = []
    if not absent.intersection(('chamber_c', 'probe_gap')) and (probe_gap >= 17 and chamber_c > 59):
        hits.append(RuleNotice('HEAT_GRADIENT', '热梯度偏高，暂停脱模', hard=True))
    if not absent.intersection(('water_pct', 'age_hours')) and (water_pct >= 47 and age_hours <= 18):
        hits.append(RuleNotice('SOFT_MIX', '湿配比且龄期不足', hard=False))
    if not absent.intersection(('cure_min', 'binder_kg')) and (cure_min < 240 and binder_kg < 285):
        hits.append(RuleNotice('WITNESS_PRESS', '要求见证复压', hard=False))
    return tuple(hits)


def expected_load(measurements):
    cure_min, chamber_c, binder_kg, water_pct, probe_gap, age_hours = measurements
    return 1 + int(probe_gap >= 12)


def dispatch_pressure(values, estimate):
    cure_min, chamber_c, binder_kg, water_pct, probe_gap, age_hours = values
    return probe_gap/35 + max(0,19-age_hours)/10 + estimate


def confidence_weight(estimate, cutoff):
    shifted = (estimate - cutoff) / max(.5, abs(cutoff) * .35)
    if shifted >= 0:
        return 1 / (1 + exp(-shifted))
    bounded = exp(shifted)
    return bounded / (1 + bounded)


def recommend(assessment, attention, policy):
    raw = assessment.raw
    data = measures(raw.input_values)
    estimate = assessment.estimate
    domain_codes = signals(data, estimate, raw.missing)
    level = confidence_weight(estimate, policy.trigger)
    cost = expected_load(data)
    if not isfinite(estimate) or not 1 <= cost <= 12:
        raise ValueError('处置量不在有效范围')
    if domain_codes and domain_codes[0].hard:
        state = '暂停'
        reason = domain_codes[0].rule_id
        summary = domain_codes[0].meaning
    elif raw.key in attention or assessment.uncertain:
        state = '人工判读'
        reason = 'OUT_OF_REFERENCE' if raw.key in attention else 'INSUFFICIENT_CALIBRATION'
        summary = '分布偏移或校准量不足，需核对原始单据'
    elif domain_codes or estimate >= policy.trigger:
        state = '候选'
        reason = domain_codes[0].rule_id if domain_codes else 'ABOVE_TRIGGER'
        summary = domain_codes[0].meaning if domain_codes else '达到本班复核阈值'
    else:
        state = '观察'
        reason = 'BELOW_TRIGGER'
        summary = '保留记录并等待下一次巡查'
    return Job(raw.key, raw.cohort, round(estimate, 4), assessment.lower, assessment.upper, cost,
               state, reason, summary, round(level, 5), tuple(item.rule_id for item in domain_codes))


def allocate(assessments, attention, policy):
    selected={}
    waiting=[]
    for sample in assessments:
        signed=recommend(sample,attention,policy)
        if signed.key in selected:
            raise ValueError('处置登记号重复')
        selected[signed.key]=signed
        if signed.state=='候选':
            waiting.append(WorkOrder(signed,sample))
    allocation=Counter()
    def defer(unit, code, explanation):
        job=unit.job
        selected[job.key]=job.change('候补',code,explanation)

    def plan(unit):
        job=unit.job
        under_group=allocation[job.cohort]+job.cost<=policy.group_quota
        under_shift=allocation.total()+job.cost<=policy.capacity
        if under_group and under_shift:
            allocation[job.cohort]+=job.cost
            selected[job.key]=job.change('已分派',job.reason,job.summary)
            return True
        low_shift='本班占用上限已达'
        low_group='本区复核位已占满'
        defer(unit,'GROUP_CAP_REACHED' if under_shift else 'CAPACITY_REACHED',low_group if under_shift else low_shift)
        return False

    def rank(unit):
        data=unit.assessment.raw.input_values
        physical=dispatch_pressure(data,unit.assessment.estimate)
        category=cube_load(data)
        return (len(unit.job.rule_hits)==0,-physical,category,-unit.job.estimate,unit.job.key)
    apply_retest_press(sorted(waiting,key=rank),plan,defer)
    if any(item.state=='候选' for item in selected.values()):
        raise ArithmeticError('存在尚未排完的作业')
    balance=policy.capacity-allocation.total()
    handoff=sorted(selected.values(),key=lambda item:(item.state!='已分派',-item.priority,item.cost,item.key))
    return Plan(tuple(handoff),policy.capacity,balance,tuple(sorted(allocation.items())))


def plan_jobs(assessments, attention, capacity, mode='balanced'):
    return allocate(assessments, frozenset(attention), Policy.select(capacity, mode))


def action_evidence(plan):
    counts = Counter(job.state for job in plan.jobs)
    status = [{'处置': state, '单量': count} for state, count in sorted(counts.items())]
    status.extend({'处置': '分区 ' + group, '额度': cost} for group, cost in plan.used_by_group)
    status += [{'处置': '剩余额度', '额度': plan.balance}]
    return status


def cube_load(raw):
    probe_gap = raw[4]
    return int(probe_gap//5)


def operating_group(assessments, progression):
    source={line.raw.key:line.raw.input_values for line in assessments}
    cells=Counter()
    for work in progression.jobs:
        if work.state != '已分派':
            continue
        band=cube_load(source[work.key])
        cells[work.cohort,band] += work.cost
    return [{ '作业区': zone, '压力机档': band, '班组用量': total } for (zone,band),total in sorted(cells.items())]
