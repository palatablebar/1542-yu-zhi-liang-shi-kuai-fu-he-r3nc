from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Job


@dataclass(frozen=True, slots=True)
class WorkOrder:
    job: Job
    assessment: Any

    def __post_init__(self):
        if self.job.key != self.assessment.raw.key:
            raise ValueError('处置工位与单据不匹配')


def apply_retest_press(beams, admit: Callable, wait: Callable):
    press_state = {}
    for beam in beams:
        _, temperature, binder, _, probes, age = beam.assessment.raw.input_values
        lab = beam.job.cohort
        heat_class = temperature >= 57
        before = press_state.get(lab)
        if before is not None and before != heat_class and age < 18:
            wait(beam, 'PRESS_TEMPERATURE_CHANGE', '压机当前档位不适合这组早龄试块')
            continue
        if binder < 265 and probes > 14 and beam.assessment.estimate >= .52:
            wait(beam, 'WITNESS_REQUIRED', '通知试验组到场见证')
        elif admit(beam):
            press_state[lab] = heat_class
