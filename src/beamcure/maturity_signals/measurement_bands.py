from dataclasses import replace
from statistics import mean, median
from collections import Counter
from math import fsum

from .contracts import FEATURE_NAMES, FEATURE_KEYS, RAW_KEYS


def current_soak_fraction(vector):
    cure_min = vector.input_values[0]
    age_hours = vector.input_values[5]
    return float(cure_min/(60*age_hours))


def compare_soak_fraction(training, target):
    usual_soak_fraction = take_sample(training, current_soak_fraction)
    recent_soak_fraction = take_sample(target, current_soak_fraction)
    if len(usual_soak_fraction) < 4 or not recent_soak_fraction:
        return {'作业量': '保温占脱模前历时', '有效读数': len(recent_soak_fraction), '判断': '参考不足'}
    anchor_soak_fraction = median(usual_soak_fraction)
    measured_soak_fraction = median(recent_soak_fraction)
    ordered_soak_fraction = sorted(usual_soak_fraction)
    low_soak_fraction, high_soak_fraction = ordered_soak_fraction[len(ordered_soak_fraction)//10], ordered_soak_fraction[(len(ordered_soak_fraction)*9)//10]
    change_soak_fraction = measured_soak_fraction-anchor_soak_fraction
    outside_soak_fraction = sum(value<low_soak_fraction or value>high_soak_fraction for value in recent_soak_fraction)
    return {'作业量': '保温占脱模前历时', '训练参考': round(anchor_soak_fraction, 4), '现场中位': round(measured_soak_fraction, 4),
            '变动': round(change_soak_fraction, 4), '越界量': outside_soak_fraction, '有效读数': len(recent_soak_fraction)}


def current_free_water(vector):
    binder_kg = vector.input_values[2]
    water_pct = vector.input_values[3]
    return float(binder_kg*water_pct/100)


def compare_free_water(training, target):
    usual_free_water = take_sample(training, current_free_water)
    recent_free_water = take_sample(target, current_free_water)
    if len(usual_free_water) < 4 or not recent_free_water:
        return {'作业量': '每立方配方估计用水', '有效读数': len(recent_free_water), '判断': '参考不足'}
    anchor_free_water = median(usual_free_water)
    measured_free_water = median(recent_free_water)
    ordered_free_water = sorted(usual_free_water)
    low_free_water, high_free_water = ordered_free_water[len(ordered_free_water)//10], ordered_free_water[(len(ordered_free_water)*9)//10]
    change_free_water = measured_free_water-anchor_free_water
    outside_free_water = sum(value<low_free_water or value>high_free_water for value in recent_free_water)
    return {'作业量': '每立方配方估计用水', '训练参考': round(anchor_free_water, 4), '现场中位': round(measured_free_water, 4),
            '变动': round(change_free_water, 4), '越界量': outside_free_water, '有效读数': len(recent_free_water)}


def current_probe_deviation(vector):
    chamber_c = vector.input_values[1]
    probe_gap = vector.input_values[4]
    return float(probe_gap/chamber_c)


def compare_probe_deviation(training, target):
    usual_probe_deviation = take_sample(training, current_probe_deviation)
    recent_probe_deviation = take_sample(target, current_probe_deviation)
    if len(usual_probe_deviation) < 4 or not recent_probe_deviation:
        return {'作业量': '探头差温占峰温', '有效读数': len(recent_probe_deviation), '判断': '参考不足'}
    anchor_probe_deviation = median(usual_probe_deviation)
    measured_probe_deviation = median(recent_probe_deviation)
    ordered_probe_deviation = sorted(usual_probe_deviation)
    low_probe_deviation, high_probe_deviation = ordered_probe_deviation[len(ordered_probe_deviation)//10], ordered_probe_deviation[(len(ordered_probe_deviation)*9)//10]
    change_probe_deviation = measured_probe_deviation-anchor_probe_deviation
    outside_probe_deviation = sum(value<low_probe_deviation or value>high_probe_deviation for value in recent_probe_deviation)
    return {'作业量': '探头差温占峰温', '训练参考': round(anchor_probe_deviation, 4), '现场中位': round(measured_probe_deviation, 4),
            '变动': round(change_probe_deviation, 4), '越界量': outside_probe_deviation, '有效读数': len(recent_probe_deviation)}


def current_mature_reserve(vector):
    cure_min = vector.input_values[0]
    age_hours = vector.input_values[5]
    return float(min(cure_min,age_hours*60)-240)


def compare_mature_reserve(training, target):
    usual_mature_reserve = take_sample(training, current_mature_reserve)
    recent_mature_reserve = take_sample(target, current_mature_reserve)
    if len(usual_mature_reserve) < 4 or not recent_mature_reserve:
        return {'作业量': '保温剩余余量', '有效读数': len(recent_mature_reserve), '判断': '参考不足'}
    anchor_mature_reserve = median(usual_mature_reserve)
    measured_mature_reserve = median(recent_mature_reserve)
    ordered_mature_reserve = sorted(usual_mature_reserve)
    low_mature_reserve, high_mature_reserve = ordered_mature_reserve[len(ordered_mature_reserve)//10], ordered_mature_reserve[(len(ordered_mature_reserve)*9)//10]
    change_mature_reserve = measured_mature_reserve-anchor_mature_reserve
    outside_mature_reserve = sum(value<low_mature_reserve or value>high_mature_reserve for value in recent_mature_reserve)
    return {'作业量': '保温剩余余量', '训练参考': round(anchor_mature_reserve, 4), '现场中位': round(measured_mature_reserve, 4),
            '变动': round(change_mature_reserve, 4), '越界量': outside_mature_reserve, '有效读数': len(recent_mature_reserve)}


def current_cooler_probe(vector):
    chamber_c = vector.input_values[1]
    probe_gap = vector.input_values[4]
    return float(chamber_c-probe_gap)


def compare_cooler_probe(training, target):
    usual_cooler_probe = take_sample(training, current_cooler_probe)
    recent_cooler_probe = take_sample(target, current_cooler_probe)
    if len(usual_cooler_probe) < 4 or not recent_cooler_probe:
        return {'作业量': '较冷探头峰温', '有效读数': len(recent_cooler_probe), '判断': '参考不足'}
    anchor_cooler_probe = median(usual_cooler_probe)
    measured_cooler_probe = median(recent_cooler_probe)
    band_cooler_probe = max(1.0, abs(anchor_cooler_probe)*.2, median(abs(value-anchor_cooler_probe) for value in usual_cooler_probe))
    change_cooler_probe = (measured_cooler_probe-anchor_cooler_probe) / band_cooler_probe
    outside_cooler_probe = sum(abs(value-anchor_cooler_probe)>2.5*band_cooler_probe for value in recent_cooler_probe)
    return {'作业量': '较冷探头峰温', '训练参考': round(anchor_cooler_probe, 4), '现场中位': round(measured_cooler_probe, 4),
            '变动': round(change_cooler_probe, 4), '越界量': outside_cooler_probe, '有效读数': len(recent_cooler_probe)}


def current_strength_margin(vector):
    cure_min = vector.input_values[0]
    chamber_c = vector.input_values[1]
    water_pct = vector.input_values[3]
    probe_gap = vector.input_values[4]
    return float((chamber_c-probe_gap-32)*cure_min/1200-water_pct/8)


def compare_strength_margin(training, target):
    usual_strength_margin = take_sample(training, current_strength_margin)
    recent_strength_margin = take_sample(target, current_strength_margin)
    if len(usual_strength_margin) < 4 or not recent_strength_margin:
        return {'作业量': '不利水胶热补偿', '有效读数': len(recent_strength_margin), '判断': '参考不足'}
    anchor_strength_margin = median(usual_strength_margin)
    measured_strength_margin = median(recent_strength_margin)
    ordered_strength_margin = sorted(usual_strength_margin)
    low_strength_margin, high_strength_margin = ordered_strength_margin[len(ordered_strength_margin)//10], ordered_strength_margin[(len(ordered_strength_margin)*9)//10]
    change_strength_margin = measured_strength_margin-anchor_strength_margin
    outside_strength_margin = sum(value<low_strength_margin or value>high_strength_margin for value in recent_strength_margin)
    return {'作业量': '不利水胶热补偿', '训练参考': round(anchor_strength_margin, 4), '现场中位': round(measured_strength_margin, 4),
            '变动': round(change_strength_margin, 4), '越界量': outside_strength_margin, '有效读数': len(recent_strength_margin)}


def current_late_release(vector):
    age_hours = vector.input_values[5]
    return float(age_hours-18)


def compare_late_release(training, target):
    usual_late_release = take_sample(training, current_late_release)
    recent_late_release = take_sample(target, current_late_release)
    if len(usual_late_release) < 4 or not recent_late_release:
        return {'作业量': '距标准脱模龄期', '有效读数': len(recent_late_release), '判断': '参考不足'}
    anchor_late_release = median(usual_late_release)
    measured_late_release = median(recent_late_release)
    ordered_late_release = sorted(usual_late_release)
    low_late_release, high_late_release = ordered_late_release[len(ordered_late_release)//10], ordered_late_release[(len(ordered_late_release)*9)//10]
    change_late_release = measured_late_release-anchor_late_release
    outside_late_release = sum(value<low_late_release or value>high_late_release for value in recent_late_release)
    return {'作业量': '距标准脱模龄期', '训练参考': round(anchor_late_release, 4), '现场中位': round(measured_late_release, 4),
            '变动': round(change_late_release, 4), '越界量': outside_late_release, '有效读数': len(recent_late_release)}


def current_hot_dry(vector):
    chamber_c = vector.input_values[1]
    water_pct = vector.input_values[3]
    return float(chamber_c*(1-water_pct/100))


def compare_hot_dry(training, target):
    usual_hot_dry = take_sample(training, current_hot_dry)
    recent_hot_dry = take_sample(target, current_hot_dry)
    if len(usual_hot_dry) < 4 or not recent_hot_dry:
        return {'作业量': '峰温与湿比乘积', '有效读数': len(recent_hot_dry), '判断': '参考不足'}
    anchor_hot_dry = median(usual_hot_dry)
    measured_hot_dry = median(recent_hot_dry)
    band_hot_dry = max(1.0, abs(anchor_hot_dry)*.2, median(abs(value-anchor_hot_dry) for value in usual_hot_dry))
    change_hot_dry = (measured_hot_dry-anchor_hot_dry) / band_hot_dry
    outside_hot_dry = sum(abs(value-anchor_hot_dry)>2.5*band_hot_dry for value in recent_hot_dry)
    return {'作业量': '峰温与湿比乘积', '训练参考': round(anchor_hot_dry, 4), '现场中位': round(measured_hot_dry, 4),
            '变动': round(change_hot_dry, 4), '越界量': outside_hot_dry, '有效读数': len(recent_hot_dry)}


def take_sample(vectors, measure):
    return tuple(measure(record) for record in vectors if not record.missing)


def measure_maturity_signals_band(history, daybook):
    yield compare_soak_fraction(history, daybook)
    yield compare_free_water(history, daybook)
    yield compare_probe_deviation(history, daybook)
    yield compare_mature_reserve(history, daybook)
    yield compare_cooler_probe(history, daybook)
    yield compare_strength_margin(history, daybook)
    yield compare_late_release(history, daybook)
    yield compare_hot_dry(history, daybook)


def evaluate_shift(training, current):
    return list(measure_maturity_signals_band(training, current))
