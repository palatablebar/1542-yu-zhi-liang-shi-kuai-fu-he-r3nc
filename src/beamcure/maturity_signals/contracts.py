from dataclasses import dataclass
from math import isfinite
from ..beam_register.contracts import BeamcureRecord as RawObservation

RAW_KEYS = ('cure_min', 'chamber_c', 'binder_kg', 'water_pct', 'probe_gap', 'age_hours')
FEATURE_KEYS = ('heat_degree', 'water_load', 'gap_rate', 'bound_water', 'maturity_age')
FEATURE_NAMES = ('有效温时积', '胶材水负荷', '单位龄期梯度', '等效胶材量', '龄期温时代理')


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')


@dataclass(frozen=True, slots=True)
class FeatureVector:
    key: str
    cohort: str
    day: int
    values: tuple[float, ...]
    factors: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PreparedRuns:
    train: tuple[FeatureVector, ...]
    calibration: tuple[FeatureVector, ...]
    replay: tuple[FeatureVector, ...]
    live: tuple[FeatureVector, ...]

    def segments(self):
        return tuple((name, getattr(self, name)) for name in ('train', 'calibration', 'replay', 'live'))


@dataclass(frozen=True, slots=True)
class Proposal:
    name: str
    field: str
    before: float
    after: float
    work: int

    def __post_init__(self):
        if self.before == self.after or not isfinite(self.after) or self.work < 0:
            raise ValueError('推演动作需要实质变动和有效额度')

    def evidence(self):
        return {'情形': self.name, '变更项': self.field, '原值': self.before,
                '置换值': self.after, '用量': self.work}

@dataclass(frozen=True, slots=True)
class MaturitySignals:
    soak_fraction: float
    free_water: float
    probe_deviation: float
    mature_reserve: float
    cooler_probe: float
    strength_margin: float
    late_release: float
    hot_dry: float

    def __post_init__(self):
        if not all(isfinite(amount) for amount in (self.soak_fraction, self.free_water, self.probe_deviation, self.mature_reserve, self.cooler_probe, self.strength_margin, self.late_release, self.hot_dry)):
            raise ValueError('预制梁批存在无效的作业量测')

    def explain(self, labels=None):
        return (
            ('保温占脱模前历时', round(self.soak_fraction, 4)),
            ('每立方配方估计用水', round(self.free_water, 4)),
            ('探头差温占峰温', round(self.probe_deviation, 4)),
            ('保温剩余余量', round(self.mature_reserve, 4)),
            ('较冷探头峰温', round(self.cooler_probe, 4)),
            ('不利水胶热补偿', round(self.strength_margin, 4)),
            ('距标准脱模龄期', round(self.late_release, 4)),
            ('峰温与湿比乘积', round(self.hot_dry, 4)),
        )
