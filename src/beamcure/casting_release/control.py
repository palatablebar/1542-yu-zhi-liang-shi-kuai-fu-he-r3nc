from collections import Counter
from math import isfinite


def accountable_plan(rows, actual_balance, starting_capacity):
    seen = set()
    counts = Counter()
    total = 0
    for row in rows:
        if row['key'] in seen:
            raise ArithmeticError('复核凭证的关联单号不唯一')
        key = row['key']
        seen.add(key)
        state = row['state']
        counts[state] += 1
        if state == '已分派':
            total += row['cost']
        if not isfinite(row['estimate']):
            raise ArithmeticError('非有限估计不能签发')
    if total + actual_balance != starting_capacity:
        raise ArithmeticError('处置清册与工位余额不符')
    return counts, total


def register_casting_release(measurements, estimate):
    cure_min = measurements['cure_min']
    chamber_c = measurements['chamber_c']
    binder_kg = measurements['binder_kg']
    water_pct = measurements['water_pct']
    probe_gap = measurements['probe_gap']
    age_hours = measurements['age_hours']
    return {
        '保温占脱模前历时': round(cure_min/(60*age_hours), 3),
        '探头差温占峰温': round(probe_gap/chamber_c, 3),
        '距标准脱模龄期': round(age_hours-18, 3),
        '峰温与湿比乘积': round(chamber_c*(1-water_pct/100), 3),
        '复核代价指标': round(probe_gap/35 + max(0,19-age_hours)/10 + estimate, 4),
    }


def document_control(rows):
    register = []
    for row in rows:
        if row['state'] not in {'已分派', '暂停', '人工判读'}:
            continue
        note = register_casting_release(row['measurements'], row['estimate'])
        register.append({'单号': row['key'], '区段': row['zone'], '处置': row['state'], **note})
    return register
