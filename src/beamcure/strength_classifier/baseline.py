from collections import defaultdict
from math import fabs, fsum
from statistics import mean, median

from .logit_model import score_kernel


def count_common_recipes(casting):
    warehouse = defaultdict(lambda: [1,2])
    for cube in casting:
        failures, total = warehouse[cube.cohort]
        warehouse[cube.cohort] = (failures + cube.outcome,total + 1)
    overall = (1+sum(cube.outcome for cube in casting))/(len(casting)+2)
    return warehouse, overall


def expected_lab_rate(reference,cube):
    by_plant, default = reference
    numbers = by_plant.get(cube.cohort)
    return default if numbers is None else numbers[0]/numbers[1]


def baseline_review(fit, training, replay):
    control = count_common_recipes(training)
    by_cohort = defaultdict(list)
    for result in replay:
        if result.observed and result.outcome in (0,1):
            forecast, _ = score_kernel(fit.parameters,result)
            local = expected_lab_rate(control, result)
            error_a, error_b = (forecast-result.outcome)**2, (local-result.outcome)**2
            by_cohort[result.cohort].append((error_a,error_b,int(result.outcome),forecast,local))
    report = []
    for location, comparisons in sorted(by_cohort.items()):
        samples = len(comparisons)
        expected = fsum(row[3] for row in comparisons)
        confirmed = sum(row[2] for row in comparisons)
        misses = sum(row[2] and row[3] < 0.49 for row in comparisons)
        base_misses = sum(row[2] and row[4] < 0.49 for row in comparisons)
        before = fsum(row[1] for row in comparisons) / samples
        after = fsum(row[0] for row in comparisons) / samples
        report.append({'回放组':location,'实绩数':samples,'估计代价':round(after,4),'业务基线代价':round(before,4),
                       '基线':'各养护线超差先验','预测阳性总量':round(expected,3),'实绩阳性数':confirmed,
                       '模型漏判':misses,'基线漏判':base_misses,
                       '相对 Brier 改善':round(1-after/before,4) if before else None})
    return report
