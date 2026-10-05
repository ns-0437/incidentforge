"""Check reported measurements exactly; never treat model prose as verified causality."""
import json

def facts(result):
    output={}
    for observation in result.get('observations',[]):
        condition=observation.get('condition')
        if not condition: continue
        if 'committed_charge_count' in observation:
            output[condition]={'committed_charge_count':observation['committed_charge_count']}
        elif 'order' in observation:
            order=observation['order'] or {}
            status=order.get('status','UNKNOWN')
            output[condition]={'order_status':status,'compensation_complete':status=='CANCELLED_DECLINED'}
        elif 'stock' in observation:
            output[condition]={'available_stock':{sku:cell['available'] for sku,cell in observation['stock'].items()}}
    return output

def experiment_facts(result,conditions):
    """Require every declared condition exactly once before summarizing results."""
    if not isinstance(result,dict) or result.get('complete') is not True:
        raise ValueError('distinguishing experiment did not complete')
    observations=result.get('observations')
    if not isinstance(observations,list):
        raise ValueError('experiment observations must be a list')
    names=[]
    for observation in observations:
        if not isinstance(observation,dict) or not isinstance(observation.get('condition'),str):
            raise ValueError('experiment observation requires a condition name')
        names.append(observation['condition'])
    if len(names)!=len(set(names)) or set(names)!=set(conditions):
        raise ValueError('experiment must observe every declared condition exactly once')
    measured=facts(result)
    if set(measured)!=set(conditions):
        raise ValueError('experiment condition is missing a supported measurement')
    return measured

def factual_conclusion(expected):
    if 'no_restart' in expected and 'order_restart' in expected:
        return ('Measured compensation states: without restart '+expected['no_restart']['order_status']+
                '; after restart '+expected['order_restart']['order_status']+
                '. These observations alone do not establish the cause.')
    if expected and all(isinstance(v,dict) and set(v)=={'committed_charge_count'} for v in expected.values()):
        return ('Measured committed charges: '+ '; '.join(k+'='+str(expected[k]['committed_charge_count']) for k in sorted(expected))+
                '. Causality remains unverified.')
    return 'Structured condition facts match the recorded measurements. Causality remains unverified.'

def check_interpretation(command,expected):
    if not expected: raise ValueError('Run an experiment before interpreting measurements')
    try: observed=command['observed_facts'] if isinstance(command['observed_facts'],dict) else json.loads(command['observed_facts'])
    except (ValueError,KeyError,TypeError): raise ValueError('observed_facts must be a JSON-encoded object')
    if json.dumps(observed,sort_keys=True)!=json.dumps(expected,sort_keys=True):
        raise ValueError('observed_facts disagree with measured facts; copy every condition exactly')
    if command.get('conclusion')!=factual_conclusion(expected):
        raise ValueError('conclusion must equal required_factual_conclusion exactly; causal claims belong in the unverified hypothesis commentary')
    # This checks the structured factual portion, not arbitrary natural-language reasoning.
    return {'facts_verified':True,'causal_prose_verified':False}

def final_decision(result):
    """Check internal consistency of an acceptance receipt, not its authenticity."""
    if not isinstance(result,dict) or result.get('complete') is not True:
        return 'invalid_evaluation'
    decision=result.get('decision')
    if decision not in ('accept_for_review','reject_behavior','reject_patch_invalid','invalid_evaluation'):
        return 'invalid_evaluation'
    if decision!='accept_for_review': return decision
    count=result.get('tests_run');cases=result.get('cases')
    if type(count) is not int or count<=0 or not isinstance(cases,list) or len(cases)!=count:
        return 'invalid_evaluation'
    if any(type(result.get(key)) is not int or result[key]!=0 for key in ('errors','failures','skipped')):
        return 'invalid_evaluation'
    names=set()
    for case in cases:
        if not isinstance(case,dict): return 'invalid_evaluation'
        name=case.get('case')
        if not isinstance(name,str) or not name.strip() or name in names: return 'invalid_evaluation'
        names.add(name)
        if case.get('decision')!='accept_for_review': return 'invalid_evaluation'
        boundary=case.get('boundary')
        if not isinstance(boundary,dict) or not boundary or any(v is not True for v in boundary.values()):
            return 'invalid_evaluation'
        properties=case.get('properties')
        if not isinstance(properties,dict) or set(properties)!={f'P{i}' for i in range(1,8)}:
            return 'invalid_evaluation'
        for prop,value in properties.items():
            if not isinstance(value,dict): return 'invalid_evaluation'
            allowed=('pass','not_applicable') if prop in ('P2','P6') else ('pass',)
            if value.get('status') not in allowed: return 'invalid_evaluation'
    return decision

DECLINE_TERMINAL='CANCELLED_DECLINED'

def _symptom_assessment(incident,observations):
    """Incident-specific reproduction verdict from observations alone.

    IF-002's order_restart condition establishes a durable COMPENSATING intent
    with the reservation confirmed HELD, then measures recovery against a
    declared deadline. A non-terminal status is only called a reproduction once
    that declared window has elapsed; before then it is an intermediate state.

    IF-001 stays undetermined: developer mode reports HTTP responses and request
    identity counts, never committed effects, and a duplicate charge cannot be
    inferred from request counts.
    """
    if incident!='IF-002':
        return ('not determined; this mode exposes HTTP observations and request identity '
                'counts, not committed-effect counts',
                'committed-effect evidence unavailable in this mode',None,
                'not measured in this mode')
    for observation in observations:
        if observation.get('condition')!='order_restart': continue
        order=observation.get('order') or {}
        status=order.get('status')
        elapsed,deadline=observation.get('elapsed_seconds'),observation.get('deadline_seconds')
        support={'condition':'order_restart','status':status,'elapsed_seconds':elapsed,
                 'deadline_seconds':deadline,'startup_seconds':observation.get('startup_seconds')}
        numeric=isinstance(elapsed,(int,float)) and isinstance(deadline,(int,float))
        if not isinstance(status,str) or not numeric:
            return ('not determined','order_restart lacks a status or a declared recovery window',
                    support,deadline if numeric else 'not recorded')
        if status==DECLINE_TERMINAL:
            return ('not observed','compensation reached '+DECLINE_TERMINAL+
                    ' within the declared recovery window',support,deadline)
        if elapsed>=deadline:
            return ('observed','status stayed '+status+', not '+DECLINE_TERMINAL+
                    ', after the declared recovery window elapsed',support,deadline)
        return ('not determined','status '+status+' is non-terminal but the declared recovery '
                'window had not elapsed; an intermediate state is not a failure',support,deadline)
    return ('not determined','no order_restart condition was executed',None,'not measured in this mode')


def reproduction_bounds(incident,spec,result):
    """Declared execution bounds and limits for one reproduction attempt.

    Execution completing is not the same as reproducing the reported symptom.
    Developer observations expose HTTP responses, request identity counts and
    order state; committed-effect counts are not available in that mode, so
    symptom reproduction is reported as undetermined rather than inferred.
    Values absent from the spec or result are marked, never invented.
    """
    observations=[o for o in (result.get('observations') or []) if isinstance(o,dict)]
    conditions=[]
    for observation in observations:
        label=observation.get('condition') or observation.get('fault')
        if label and str(label) not in conditions: conditions.append(str(label))
    stated=list(result.get('limitations') or [])
    if result.get('note'): stated.append(result['note'])
    assessment,criterion,support,bound=_symptom_assessment(incident,observations)
    return {'incident':incident,
            'executed_conditions':conditions or ['not recorded'],
            'reset':spec.get('reset','not recorded'),
            'workload':spec.get('workload','not recorded'),
            'declared_limits':spec.get('limits') or {},
            'repetitions':spec.get('repetitions','not recorded'),
            'execution':'complete' if result.get('complete') is True else 'incomplete',
            'symptom_reproduction':assessment,
            'symptom_criterion':criterion,
            'symptom_observation':support,
            'recovery_bound':bound,
            'stated_limitations':stated,
            'scope':'Finite authored fixture conditions and faults. This does not establish '
                    'reproduction of arbitrary production incidents.'}
