from dataclasses import dataclass
from math import sqrt, fsum
from statistics import median


@dataclass(frozen=True, slots=True)
class DomainStudy:
    counts: tuple[int, int, int]
    rate: float | None
    midpoint: float | None
    expected: float | None
    drift: float | None

def recipe_shift_domains(vectors):
    soak_fraction = []
    free_water = []
    probe_deviation = []
    mature_reserve = []
    cooler_probe = []
    strength_margin = []
    late_release = []
    hot_dry = []
    for measurement in vectors:
        unobserved = frozenset(measurement.missing)
        cure_min, chamber_c, binder_kg, water_pct, probe_gap, age_hours = measurement.input_values
        if unobserved.isdisjoint(('cure_min', 'probe_gap', 'age_hours')):
            soak_fraction.append((round(cure_min/(60*age_hours), 4), probe_gap>=14))
        if unobserved.isdisjoint(('binder_kg', 'water_pct', 'age_hours')):
            free_water.append((round(binder_kg*water_pct/100, 4), age_hours<=16))
        if unobserved.isdisjoint(('chamber_c', 'water_pct', 'probe_gap')):
            probe_deviation.append((round(probe_gap/chamber_c, 4), water_pct>=46))
        if unobserved.isdisjoint(('cure_min', 'binder_kg', 'age_hours')):
            mature_reserve.append((round(min(cure_min,age_hours*60)-240, 4), binder_kg<=290))
        if unobserved.isdisjoint(('chamber_c', 'probe_gap')):
            cooler_probe.append((round(chamber_c-probe_gap, 4), chamber_c<49))
        if unobserved.isdisjoint(('cure_min', 'chamber_c', 'water_pct', 'probe_gap')):
            strength_margin.append((round((chamber_c-probe_gap-32)*cure_min/1200-water_pct/8, 4), probe_gap>=14))
        if unobserved.isdisjoint(('age_hours',)):
            late_release.append((round(age_hours-18, 4), age_hours<=16))
        if unobserved.isdisjoint(('chamber_c', 'water_pct')):
            hot_dry.append((round(chamber_c*(1-water_pct/100), 4), water_pct>=46))
    return {
        '保温占脱模前历时 · 双探头偏差': tuple(soak_fraction),
        '每立方配方估计用水 · 脱模观察期短': tuple(free_water),
        '探头差温占峰温 · 高水胶比': tuple(probe_deviation),
        '保温剩余余量 · 胶材低库存配方': tuple(mature_reserve),
        '较冷探头峰温 · 偏冷蒸养': tuple(cooler_probe),
        '不利水胶热补偿 · 双探头偏差': tuple(strength_margin),
        '距标准脱模龄期 · 脱模观察期短': tuple(late_release),
        '峰温与湿比乘积 · 高水胶比': tuple(hot_dry),
    }


def evaluate_domains(training, current):
    references = recipe_shift_domains(training)
    activity = recipe_shift_domains(current)
    diagnostics = []
    for domain, observed in activity.items():
        baseline = references.get(domain, ())
        study = characterize(baseline, observed)
        diagnostics.append({'观察维度': domain, '训练有效量': study.counts[0], '当班有效量': study.counts[1],
                            '越线量':study.counts[2], '越线比例':study.rate, '参考中位':study.midpoint,
                            '当班中位':study.expected, '相对训练变化':study.drift})
    return diagnostics


def characterize(before, after):
    history = tuple(value for value, _ in before)
    observed = tuple(value for value, _ in after)
    violating = sum(flag for _, flag in after)
    old = median(history) if history else None
    new = median(observed) if observed else None
    pct = round(violating / len(after), 4) if after else None
    movement = round(new - old, 4) if old is not None and new is not None else None
    return DomainStudy((len(before),len(after),violating),pct,old,new,movement)
