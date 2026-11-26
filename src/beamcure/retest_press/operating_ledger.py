from collections import defaultdict
from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True, slots=True)
class WitnessNeed:
    batch: str
    samples: int
    bench_split: int
    probe_hold: bool
    risk_partition: str
    maturity: float


def cube_requirement(record):
    measures = record['measurements']
    needed = {'cure_min', 'chamber_c', 'probe_gap', 'binder_kg', 'age_hours', 'water_pct'}
    if needed.intersection(record['unmeasured']):
        return None
    degree_hours = (measures['chamber_c'] - 15) * measures['cure_min'] / 60
    thermal_hold = 'HEAT_GRADIENT' in record['hits']
    immature = degree_hours < 155 or measures['age_hours'] < 16
    wetter = measures['water_pct'] >= 47 and measures['binder_kg'] < 320
    risk = record['estimate'] >= .49
    if thermal_hold:
        witness = '梯度见证'
        cubes = 3
    elif immature or wetter:
        witness = '同条件复压'
        cubes = 2 + int(immature and wetter)
    elif risk:
        witness = '随机见证加测'
        cubes = 2
    else:
        witness = '常规存档'
        cubes = 1
    press_sets = ceil(cubes / 2) if thermal_hold else 1
    return WitnessNeed(record['key'], cubes, press_sets, thermal_hold, witness, degree_hours)


def operating_ledger(rows):
    batches = defaultdict(list)
    notes = []
    for record in rows:
        request = cube_requirement(record)
        casting = record['zone']
        if request is None:
            notes.append({'业务安排': '补齐蒸养记录', '关联单据': record['key'], '生产线': casting})
            continue
        batches[casting].append((record, request))
    for casting, pending in sorted(batches.items()):
        turn = 0
        sample_count = 0
        witnessed = 0
        unscheduled = 0
        for record, check in sorted(pending, key=lambda group: (not group[1].probe_hold, group[1].maturity, group[1].batch)):
            eligible = record['state'] == '已分派' and not check.probe_hold
            slot = turn + 1 if eligible else None
            if slot is not None:
                turn += check.bench_split
                sample_count += check.samples
                witnessed += check.samples > 1
            elif check.risk_partition != '常规存档':
                unscheduled += check.samples
            if check.risk_partition != '常规存档':
                notes.append({'业务安排': check.risk_partition, '关联单据': check.batch, '生产线': casting,
                              '温时积': round(check.maturity, 1), '所需试块': check.samples,
                              '复压起始组': slot, '待现场签认': True})
        notes.append({'业务安排': '试块槽位结算', '生产线': casting, '已排复压试块': sample_count,
                      '已排见证批次': witnessed, '未排见证试块': unscheduled, '复压占组': turn})
    return notes
