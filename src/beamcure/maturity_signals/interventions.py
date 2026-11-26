from dataclasses import replace
from statistics import median

from .contracts import MaturitySignals, Proposal


def measure_maturity_signals(values) -> MaturitySignals:
    cure_min, chamber_c, binder_kg, water_pct, probe_gap, age_hours = values
    return MaturitySignals(
        soak_fraction=cure_min/(60*age_hours),
        free_water=binder_kg*water_pct/100,
        probe_deviation=probe_gap/chamber_c,
        mature_reserve=min(cure_min,age_hours*60)-240,
        cooler_probe=chamber_c-probe_gap,
        strength_margin=(chamber_c-probe_gap-32)*cure_min/1200-water_pct/8,
        late_release=age_hours-18,
        hot_dry=chamber_c*(1-water_pct/100),
    )


def propose_retest_press(values, missing=()):
    cure_min, chamber_c, binder_kg, water_pct, probe_gap, age_hours = values
    if 'age_hours' not in missing and (age_hours<=30):
        yield Proposal('延长两小时待拆', 'age_hours', age_hours, min(32,age_hours+2), 1)
    if 'cure_min' not in missing and (cure_min<=555 and chamber_c<64):
        yield Proposal('低温补四十五分钟', 'cure_min', cure_min, min(600,cure_min+45), 2)
    if 'probe_gap' not in missing and (probe_gap>=7):
        yield Proposal('暂停脱模并核对双探头', 'probe_gap', probe_gap, max(1,probe_gap-4), 2)
    if 'water_pct' not in missing and (water_pct>=34):
        yield Proposal('试拌降低下批水胶比', 'water_pct', water_pct, max(30,water_pct-3), 3)
