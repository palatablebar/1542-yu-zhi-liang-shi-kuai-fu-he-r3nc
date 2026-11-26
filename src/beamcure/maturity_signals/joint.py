from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointAction:
    case: str
    work_units: int
    notes: str
    changes: dict[str, tuple[float, float]]

    def evidence(self, old_value, new_value, extrapolates):
        return {'联动推演':self.case, '用量':self.work_units, '先决条件':self.notes,
                '原预测':round(old_value,4), '替换预测':round(new_value,4),
                '变化':round(new_value-old_value,4), '超训练域':bool(extrapolates),
                '联动量测':{item:{'原值':before,'替换值':after} for item,(before,after) in self.changes.items()}}


def simulate_reschedule_mold(readings, invalid):
    cure_min, age_hours = readings[0], readings[5]
    if invalid.intersection(('cure_min', 'age_hours')):
        return None
    if not (cure_min<=540 and age_hours<=28):
        return None
    cure_min_adjusted = cure_min+50
    age_hours_adjusted = age_hours+3
    inspected = {
        'cure_min': (cure_min, cure_min_adjusted),
        'age_hours': (age_hours, age_hours_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('保温延长加龄期', 2, '移至下班次拆模并追加蒸养', inspected)
    return None


def simulate_recheck_probes(readings, invalid):
    cure_min, probe_gap = readings[0], readings[4]
    if invalid.intersection(('cure_min', 'probe_gap')):
        return None
    if not (probe_gap>=6 and cure_min<=555):
        return None
    probe_gap_adjusted = probe_gap-4
    cure_min_adjusted = cure_min+30
    inspected = {
        'probe_gap': (probe_gap, probe_gap_adjusted),
        'cure_min': (cure_min, cure_min_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('回查探头补时', 2, '同档温度二点补校', inspected)
    return None


def simulate_limit_thermal_drift(readings, invalid):
    chamber_c, probe_gap = readings[1], readings[4]
    if invalid.intersection(('chamber_c', 'probe_gap')):
        return None
    if not (chamber_c>=47 and probe_gap>=8):
        return None
    chamber_c_adjusted = chamber_c-7
    probe_gap_adjusted = probe_gap-5
    inspected = {
        'chamber_c': (chamber_c, chamber_c_adjusted),
        'probe_gap': (probe_gap, probe_gap_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('维持双探头均温', 3, '以低峰温延长均热段', inspected)
    return None


def simulate_use_drier_recipe(readings, invalid):
    binder_kg, water_pct = readings[2], readings[3]
    if invalid.intersection(('binder_kg', 'water_pct')):
        return None
    if not (water_pct>=36 and binder_kg<=380):
        return None
    water_pct_adjusted = water_pct-4
    binder_kg_adjusted = binder_kg+20
    inspected = {
        'water_pct': (water_pct, water_pct_adjusted),
        'binder_kg': (binder_kg, binder_kg_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('下一配方降水胶比', 3, '仅用于下一批配比走查', inspected)
    return None


def simulate_retain_cold_cube(readings, invalid):
    chamber_c, age_hours = readings[1], readings[5]
    if invalid.intersection(('chamber_c', 'age_hours')):
        return None
    if not (chamber_c<=67 and age_hours<=29):
        return None
    chamber_c_adjusted = chamber_c+5
    age_hours_adjusted = age_hours+2
    inspected = {
        'chamber_c': (chamber_c, chamber_c_adjusted),
        'age_hours': (age_hours, age_hours_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('低温组压前保留', 2, '加温后复核延迟龄期', inspected)
    return None


def options(values, missing):
    measurements=tuple(values)
    unobserved=frozenset(missing)
    cases=(
        simulate_reschedule_mold(measurements, unobserved),
        simulate_recheck_probes(measurements, unobserved),
        simulate_limit_thermal_drift(measurements, unobserved),
        simulate_use_drier_recipe(measurements, unobserved),
        simulate_retain_cold_cube(measurements, unobserved),
    )
    return tuple(action for action in cases if action is not None)
