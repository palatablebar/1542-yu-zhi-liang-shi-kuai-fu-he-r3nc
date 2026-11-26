from math import exp, log, fsum, sqrt
from statistics import median, mean, quantiles

from .logit_model import score_kernel
from dataclasses import replace


def explain_strength_classifier(fit, calibration, replay, live):
    model_weights = fit.parameters
    by_mix = {}
    difference = 0.0
    count = 0
    for cube in replay:
        if not cube.observed or cube.outcome is None:
            continue
        risk, terms = score_kernel(model_weights,cube)
        unadjusted = score_kernel(model_weights, replace(cube,values=(cube.values[0],cube.values[1],0.,cube.values[3],cube.values[4])))[0]
        source = cube.cohort, '大温差' if cube.input_values[4]>=13 else '常温差'
        by_mix.setdefault(source, []).append((risk,cube.outcome,terms[2]))
        count += 1
        difference += abs(risk-unadjusted)
    summary = [{'验算': '抹去温差特征的平均风险变化', '有效试块': count, '平均变化': round(difference/count,5) if count else None}]
    for (workshop, band), cases in sorted(by_mix.items()):
        summary.append({'蒸养线':workshop,'温差档':band,'对照批':len(cases),
                        '模型风险':round(mean(p for p,y,x in cases),4), '强度不合格比':round(mean(y for p,y,x in cases),4),
                        '探头贡献':round(median(x for p,y,x in cases),4)})
    return summary
