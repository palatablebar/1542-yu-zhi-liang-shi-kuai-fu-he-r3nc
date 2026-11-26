from math import exp
import numpy as np


def logistic(log_odds):
    if log_odds >= 0:
        return 1 / (1 + exp(-log_odds))
    small = exp(log_odds)
    return small / (1 + small)


def fit_kernel(rows):
    target = np.asarray([beam.outcome for beam in rows], dtype=float)
    design = np.asarray([(1, *beam.values) for beam in rows], dtype=float)
    penalty = np.identity(design.shape[1]) * 1.1
    penalty[0, 0] = .035
    parameters = np.zeros(design.shape[1])
    objectives = []
    for step in range(30):
        logits = design @ parameters
        probability = np.asarray([logistic(float(item)) for item in logits])
        curvature = np.maximum(probability * (1 - probability), 1e-9)
        information = (design.T * curvature) @ design + penalty
        residual = design.T @ (target - probability) - penalty @ parameters
        movement = np.linalg.solve(information, residual)
        cost_before = np.sum(np.logaddexp(0, logits) - target * logits) + .5 * parameters @ penalty @ parameters
        fraction = 1.0
        while fraction >= 2 ** -12:
            proposal = parameters + fraction * movement
            alternate = design @ proposal
            cost_after = np.sum(np.logaddexp(0, alternate) - target * alternate) + .5 * proposal @ penalty @ proposal
            if cost_after <= cost_before + 1e-10:
                parameters = proposal
                objectives.append(float(cost_after))
                break
            fraction *= .5
        if np.linalg.norm(fraction * movement) < 1e-7:
            break
    return tuple(map(float, parameters)), (('试块阳性', int(target.sum())), ('收敛步数', len(objectives)),
                                         ('最终惩罚损失', objectives[-1] if objectives else float(cost_before)))


def score_kernel(coefficients, sample):
    impacts = tuple(weight * value for weight, value in zip(coefficients[1:], sample.values, strict=True))
    return logistic(coefficients[0] + sum(impacts)), impacts
