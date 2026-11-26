def collect_press_witness(measures, missing, estimate):
    cure_min = measures['cure_min']
    probe_gap = measures['probe_gap']
    if not (cure_min<275 or probe_gap>11):
        return None
    value=probe_gap
    return {'现场复核':'见证员到场','可复查值':round(value,3),'单位':'℃','归档要求':'登记见证员和试块身份',
            '需补测':not set(missing).isdisjoint(('cure_min', 'probe_gap'))}


def collect_heat_soak(measures, missing, estimate):
    chamber_c = measures['chamber_c']
    probe_gap = measures['probe_gap']
    if not (chamber_c>59):
        return None
    value=chamber_c-probe_gap
    return {'现场复核':'蒸养室复读','可复查值':round(value,3),'单位':'℃','归档要求':'现场对照两个温度探头',
            '需补测':not set(missing).isdisjoint(('chamber_c', 'probe_gap'))}


def collect_demold_age(measures, missing, estimate):
    age_hours = measures['age_hours']
    if not (age_hours<20):
        return None
    value=18-age_hours
    return {'现场复核':'龄期计时','可复查值':round(value,3),'单位':'小时','归档要求':'等龄期时钟确认再动梁',
            '需补测':not set(missing).isdisjoint(('age_hours',))}


def collect_mix_ratio(measures, missing, estimate):
    binder_kg = measures['binder_kg']
    water_pct = measures['water_pct']
    if not (water_pct>=44):
        return None
    value=binder_kg*water_pct/100
    return {'现场复核':'配方审核','可复查值':round(value,3),'单位':'kg/m³','归档要求':'比对胶材领用单与车间用水单',
            '需补测':not set(missing).isdisjoint(('binder_kg', 'water_pct'))}


def check_casting_release(records):
    guide = []
    for ticket in records:
        if ticket['state'] not in ('已分派','暂停','人工判读'):
            continue
        measures=ticket['measurements']
        absent=ticket['unmeasured']
        estimate=ticket['estimate']
        checks = (
            collect_press_witness(measures,absent,estimate),
            collect_heat_soak(measures,absent,estimate),
            collect_demold_age(measures,absent,estimate),
            collect_mix_ratio(measures,absent,estimate),
        )
        required=tuple(check for check in checks if check is not None)
        if not required:
            continue
        review=ticket['key']
        for check in required:
            guide.append({'签收单':review,'作业区':ticket['zone'],'处置':ticket['state'],**check})
    return guide
