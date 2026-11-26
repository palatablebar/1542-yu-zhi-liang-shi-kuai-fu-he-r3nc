from dataclasses import dataclass

FIELDS = {'cure_min': ('有效保温', 'min', 100, 600),
 'chamber_c': ('蒸养峰温', '℃', 32, 74),
 'binder_kg': ('胶凝料用量', 'kg/m³', 235, 410),
 'water_pct': ('水胶质量比', '%', 30, 57),
 'probe_gap': ('两探头温差', '℃', 1, 22),
 'age_hours': ('脱模前龄期', 'h', 9, 32)}
LIMITS = {'result_max': 1}


class MeasureIssue(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f'{field}:{code}')
        self.field = field
        self.code = code


@dataclass(frozen=True, slots=True)
class BeamcureRecord:
    key: str
    cohort: str
    day: int
    received: int
    revision: int
    result_day: int | None
    outcome: float | None
    observed: bool
    cure_min: float | None
    chamber_c: float | None
    binder_kg: float | None
    water_pct: float | None
    probe_gap: float | None
    age_hours: float | None

    def signature(self):
        return (self.key, self.cohort, self.day, self.revision, self.result_day, self.outcome, self.observed,
                *(getattr(self, key) for key in FIELDS))


@dataclass(frozen=True, slots=True)
class Issue:
    source_row: int
    key: str
    field: str
    code: str

    def evidence(self):
        return {'行号': self.source_row, '单号': self.key, '字段': FIELDS.get(self.field, (self.field,))[0],
                '原因': self.code}


@dataclass(frozen=True, slots=True)
class DecodeResult:
    entries: tuple[BeamcureRecord, ...]
    issues: tuple[Issue, ...]
    source_rows: int
