"""Provider action syntax constraints; execution validators remain authoritative."""
from .workspace import EDITABLE,READABLE


def action_format(allowed,targets,measured_facts,required_read_path=None):
    def obj(properties):
        return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    def measured(value):
        if isinstance(value,dict): return obj({k:measured(v) for k,v in value.items()})
        return {'enum':[value]}
    text={'type':'string'}
    fields={
        'read':{'path':{'type':'string','enum':[required_read_path] if required_read_path else sorted(READABLE)}},
        'search':{'query':text},
        'replace':{'path':{'type':'string','enum':sorted(EDITABLE)},'old':text,'new':text,'reason':text},
        'test':{},'validate':{},'experiment':{},'finish':{'summary':text},
        'interpret':{'conclusion':text,'supported':text,'weakened':text,'uncertainty':text,'observed_facts':measured(measured_facts)},
    }
    assertions=[]
    for target in targets:
        paths=[f['path'] for f in target['fields']]
        if paths:
            assertions.append(obj({'name':text,'condition':{'type':'string','enum':[target['condition']]},
                'path':{'type':'string','enum':paths},
                'equals':{'anyOf':[{'type':t} for t in ('string','integer','boolean','null')]}}))
    if assertions:
        fields['developer_test']={'reason':text,'spec':obj({'assertions':{'type':'array','minItems':1,'maxItems':12,
            'items':{'anyOf':assertions}}})}
    variants=[obj({'action':{'type':'string','enum':[name]},**fields[name]}) for name in allowed if name in fields]
    return {'type':'json_schema','json_schema':{'name':'incident_action','strict':True,'schema':{'anyOf':variants}}}
