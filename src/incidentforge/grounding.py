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

def factual_conclusion(expected):
    if 'no_restart' in expected and 'order_restart' in expected:
        return ('Measured compensation states: without restart '+expected['no_restart']['order_status']+
                '; after restart '+expected['order_restart']['order_status']+
                '. These observations alone do not establish the cause.')
    return 'Measured condition facts: '+json.dumps(expected,sort_keys=True,separators=(',',':'))+'. Causality remains unverified.'

def check_interpretation(command,expected):
    if not expected: raise ValueError('Run an experiment before interpreting measurements')
    try: observed=json.loads(command['observed_facts'])
    except (ValueError,KeyError,TypeError): raise ValueError('observed_facts must be a JSON-encoded object')
    if json.dumps(observed,sort_keys=True)!=json.dumps(expected,sort_keys=True):
        raise ValueError('observed_facts disagree with measured facts; copy every condition exactly')
    if command.get('conclusion')!=factual_conclusion(expected):
        raise ValueError('conclusion must equal required_factual_conclusion exactly; causal claims belong in the unverified hypothesis commentary')
    # This checks the structured factual portion, not arbitrary natural-language reasoning.
    return {'facts_verified':True,'causal_prose_verified':False}
