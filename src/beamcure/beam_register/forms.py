from collections.abc import Mapping
from decimal import Decimal

from .contracts import MeasureIssue


from dataclasses import dataclass


def form_number(form, sheet, name, minimum, maximum):
    from .service import number

    table = form.get(sheet)
    if not isinstance(table, Mapping):
        raise MeasureIssue(sheet, 'FORM_SECTION_REQUIRED')
    return Decimal(str(number(table.get(name), name, minimum, maximum)))


@dataclass(frozen=True, slots=True)
class BeamRegisterSheet:
    soak_seconds: Decimal
    peak_deci_c: Decimal
    binder_per_batch: Decimal
    water_permille: Decimal
    dual_probe_deci_c: Decimal
    demold_age_minutes: Decimal

    def fields(self):
        return {
            'cure_min': float(self.soak_seconds) / 60,
            'chamber_c': float(self.peak_deci_c) / 10,
            'binder_kg': float(self.binder_per_batch) / 1000,
            'water_pct': float(self.water_permille) / 10,
            'probe_gap': float(self.dual_probe_deci_c) / 10,
            'age_hours': float(self.demold_age_minutes) / 60,
        }

    def validation(self):
        fields = self.fields()
        cure_min = fields['cure_min']
        chamber_c = fields['chamber_c']
        binder_kg = fields['binder_kg']
        water_pct = fields['water_pct']
        probe_gap = fields['probe_gap']
        age_hours = fields['age_hours']
        thermal_reserve = age_hours*60-cure_min
        low_probe = chamber_c-probe_gap
        water_litres = binder_kg*water_pct/100
        batch_consistency = probe_gap/(1+cure_min/60)
        alerts = []
        if thermal_reserve < 0:
            alerts.append(('demold_age_minutes', 'SOAK_EXCEEDS_CUBE_AGE'))
        if low_probe < 15:
            alerts.append(('peak_deci_c', 'DISTANT_PROBE_NOT_IN_CHAMBER'))
        if water_litres > 210 and batch_consistency > 3.5:
            alerts.append(('water_permille', 'WATER_LOG_NEEDS_RECHECK'))
        return tuple(alerts)


def read_beam_register(form):
    return BeamRegisterSheet(
        soak_seconds=form_number(form, '蒸养抄表', 'soak_seconds', 6000, 36000),
        peak_deci_c=form_number(form, '蒸养抄表', 'peak_deci_c', 320, 740),
        binder_per_batch=form_number(form, '待压试块', 'binder_per_batch', 235000, 410000),
        water_permille=form_number(form, '待压试块', 'water_permille', 300, 570),
        dual_probe_deci_c=form_number(form, '脱模记录', 'dual_probe_deci_c', 10, 220),
        demold_age_minutes=form_number(form, '脱模记录', 'demold_age_minutes', 540, 1920),
    )


def explicit_rows(form):
    if not isinstance(form, Mapping):
        raise MeasureIssue('form', 'FORM_OBJECT_REQUIRED')
    note = read_beam_register(form)
    return note.fields(), note.validation()


def check_native_history(source):
    if not isinstance(source, Mapping) or 'form' not in source:
        return source
    if any(key in source for key in ('cure_min', 'chamber_c', 'binder_kg', 'water_pct', 'probe_gap', 'age_hours')):
        raise MeasureIssue('form','MIXED_FORM_AND_FLAT_READING')
    converted, flags = explicit_rows(source['form'])
    if flags:
        raise MeasureIssue(*flags[0])
    return {**source, **converted}
