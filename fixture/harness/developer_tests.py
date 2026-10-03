"""Candidate-authored declarative assertions over public developer observations.
No eval/import/shell; assertions cannot alter trusted workload or final verification.
"""
import json

def validate(spec):
    if not isinstance(spec,dict) or set(spec)!={'assertions'}: raise ValueError('developer test requires assertions')
    if not isinstance(spec['assertions'],list) or not 1<=len(spec['assertions'])<=12: raise ValueError('1–12 assertions required')
    for a in spec['assertions']:
        if not isinstance(a,dict) or set(a)!={'name','condition','path','equals'}: raise ValueError('assertion fields')
        if any(not isinstance(a[k],str) or not 0<len(a[k])<=160 for k in ('name','condition','path')): raise ValueError('assertion text')
        if len(a['path'].split('.'))>6 or any(not p.replace('_','').isalnum() for p in a['path'].split('.')): raise ValueError('assertion path')
        if type(a['equals']) not in (str,int,bool,type(None)): raise ValueError('expected scalar')
    return spec

def validate_targets(spec,observations):
    """Author only against fields actually exposed by the developer workload."""
    for assertion in spec['assertions']:
        matches=[o for o in observations if o.get('condition',o.get('fault'))==assertion['condition']]
        if len(matches)!=1: raise ValueError('assertion condition must identify one observed developer condition')
        value=matches[0]
        for part in assertion['path'].split('.'):
            if not isinstance(value,dict) or part not in value:
                raise ValueError('assertion path must exist in the selected developer observation')
            value=value[part]
    return spec

def execute(path,result):
    if not path.exists(): return {'authored':False,'assertions':[]}
    if path.is_symlink() or path.stat().st_size>8192: raise ValueError('developer tests bound')
    spec=validate(json.loads(path.read_text(encoding='utf-8')))
    outcomes=[]
    for a in spec['assertions']:
        matches=[o for o in result.get('observations',[]) if o.get('condition',o.get('fault'))==a['condition']]
        actual=None;found=len(matches)==1
        if found:
            actual=matches[0]
            for part in a['path'].split('.'):
                if not isinstance(actual,dict) or part not in actual: found=False;actual=None;break
                actual=actual[part]
        outcomes.append({'name':a['name'],'passed':found and type(actual)==type(a['equals']) and actual==a['equals'],
                         'actual':actual,'expected':a['equals'],'path_found':found})
    return {'authored':True,'assertions':outcomes,'passed':all(o['passed'] for o in outcomes),
            'scope':'Developer assertions only; independent protected verdict unchanged.'}
