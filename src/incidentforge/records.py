"""Strict versioned records and model action validation; no executable tool strings."""
from datetime import datetime,timezone
import hashlib
import json
import uuid

FIELDS={
 'IncidentBundle':{'revision','image_digest','lock_hash','topology','config','evidence_refs','initial_state_hash','public_contract_hash','declared_gaps'},
 'Hypothesis':{'mechanism','symbols','supporting_refs','counterevidence','alternatives','predicted_signatures','distinguishing_experiment','confidence_basis'},
 'ExperimentSpec':{'question','baseline','reset','intervention','controlled_variables','workload','predictions','repetitions','reason','limits'},
 'ExperimentResult':{'spec_hash','backend','reset_result','observations','completion','completeness','violations','resources','interpretation_author'},
 'PatchCandidate':{'base_revision','diff_hash','allowed_paths','migration','rationale','developer_tests'},
 'ValidationReport':{'candidate_hash','evaluator_version','conditions','properties','boundary_status','costs','decision','limitations'},
}
DECISIONS={'accept_for_review','reject_behavior','reject_patch_invalid','unresolved','invalid_evaluation'}
LISTS={
 'IncidentBundle':{'topology','evidence_refs','declared_gaps'},
 'Hypothesis':{'symbols','supporting_refs','counterevidence','alternatives','predicted_signatures'},
 'ExperimentSpec':{'controlled_variables'},'ExperimentResult':{'violations'},
 'PatchCandidate':{'allowed_paths','migration'},'ValidationReport':{'properties','limitations'}}
OBJECTS={'IncidentBundle':{'config'},'Hypothesis':set(),'ExperimentSpec':{'predictions','limits'},
 'ExperimentResult':{'observations','resources'},'PatchCandidate':{'developer_tests'},'ValidationReport':{'costs'}}

def validate_data(kind,data):
    if not isinstance(data,dict) or set(data)!=FIELDS[kind]: raise ValueError('record fields: '+kind)
    for key,value in data.items():
        expected=list if key in LISTS[kind] else dict if key in OBJECTS[kind] else int if key=='repetitions' else str
        if type(value) is not expected: raise ValueError(kind+'.'+key+' must be '+expected.__name__)
        if expected is str and not value.strip(): raise ValueError(kind+'.'+key+' cannot be empty')
        if expected is list and key not in {'properties','migration','violations'} and any(type(x) is not str for x in value):
            raise ValueError(kind+'.'+key+' must contain strings')
    if kind=='ExperimentSpec':
        if not data['predictions'] or not data['limits']: raise ValueError('predictions and limits required')
        if any(type(v) is not int or v<=0 for v in data['limits'].values()): raise ValueError('positive integer limits required')
    if kind=='ValidationReport' and data['boundary_status'] not in ('pass','fail','unverified'): raise ValueError('boundary status')

def encoded(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value): return hashlib.sha256(encoded(value)).hexdigest()

def record(kind,run_id,data,artifacts=()):
    if kind not in FIELDS or set(data)!=FIELDS[kind]: raise ValueError('record fields: '+kind)
    validate_data(kind,data)
    if kind=='ValidationReport' and data['decision'] not in DECISIONS: raise ValueError('decision')
    if kind=='ExperimentSpec' and (type(data['repetitions']) is not int or not 1<=data['repetitions']<=3):
        raise ValueError('repetition bound')
    encoded(data)
    return {'schema_version':1,'kind':kind,'run_id':run_id,'record_id':uuid.uuid4().hex,
            'timestamp_utc':datetime.now(timezone.utc).isoformat(),'artifacts':list(artifacts),'data':data}

def action(raw):
    if not isinstance(raw,str) or len(raw.encode())>48000: raise ValueError('action size')
    obj=json.loads(raw)
    if not isinstance(obj,dict): raise ValueError('action object required')
    fields={'read':{'action','path'},'search':{'action','query'},
            'replace':{'action','path','old','new','reason'},'test':{'action'},'finish':{'action','summary'},
            'interpret':{'action','conclusion','supported','weakened','uncertainty','observed_facts'},'validate':{'action'},'experiment':{'action'},
            'developer_test':{'action','spec','reason'}}
    kind=obj.get('action')
    if not isinstance(kind,str) or kind not in fields: raise ValueError('unsupported action')
    if set(obj)!=fields[kind]: raise ValueError('required fields for '+kind+': '+', '.join(sorted(fields[kind])))
    structured={'interpret':'observed_facts','developer_test':'spec'}.get(kind)
    for key,value in obj.items():
        if key==structured and isinstance(value,dict): continue
        if not isinstance(value,str): raise ValueError(key+' must be a string'+(' or object' if key==structured else ''))
    if kind=='interpret' and any(isinstance(v,str) and not v.strip() for v in obj.values()): raise ValueError('interpretation fields required')
    if kind=='replace' and (not obj['old'] or len(obj['new'].encode())>24000): raise ValueError('edit bound')
    if kind=='search' and (not obj['query'] or len(obj['query'])>128): raise ValueError('search bound')
    return obj
