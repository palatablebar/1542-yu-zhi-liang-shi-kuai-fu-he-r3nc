from beamcure.pipeline import preview
from beamcure.retest_press.service import operating_ledger


def note(key, measures, *, zone='甲区', state='已分派', estimate=0, hits=(), missing=()):
    return {'key':key,'zone':zone,'state':state,'estimate':estimate,'hits':hits,
            'unmeasured':missing,'measurements':dict(zip(('cure_min', 'chamber_c', 'binder_kg', 'water_pct', 'probe_gap', 'age_hours'),measures,strict=True))}


def test_field_plan_is_visible_and_references_real_tickets():
    desk = preview()
    plan = desk['sections'][6]
    assert plan['operating_title'] == '试块见证排组'
    assert plan['operating_rows']
    scoped = {item['关联单据'] for item in plan['operating_rows'] if '关联单据' in item}
    assert scoped and scoped <= {row['key'] for row in desk['rows']}
    assert all(item['业务安排'] for item in plan['operating_rows'])


def test_thermal_hold_does_not_occupy_a_press_slot():
    gradient = note('CL-1',(210,67,280,49,19,13),estimate=.9,state='暂停',hits=('HEAT_GRADIENT',))
    witness = note('CL-2',(180,42,274,52,8,14),estimate=.84)
    result = operating_ledger([gradient,witness])
    needs = {row.get('关联单据'):row for row in result}
    assert needs['CL-1']['所需试块']==3 and needs['CL-1']['复压起始组'] is None
    assert needs['CL-2']['复压起始组']==1
    assert result[-1]['未排见证试块']==3
