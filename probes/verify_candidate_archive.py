"""Recompute remote protected verdicts in a restricted reader, never on the host."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from probes.verify_remote_evidence import unpack
from evaluation.verifier import evaluate

def main():
    archive=Path(sys.argv[1]);expected=sys.argv[2]
    if archive.stat().st_size>16_000_000 or hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
        raise ValueError('archive hash')
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);unpack(archive,root)
        report=json.loads((root/'result/result.json').read_text())
        checked=[]
        for path in sorted((root/'result').glob('*/manifest.json')):
            old=json.loads((path.parent/'validation.json').read_text())
            actual=evaluate(path.parent,old['manifest_sha256'],old['boundary'])
            if actual['decision']!=old['decision'] or actual['properties']!=old['properties']:
                raise ValueError('recomputed verdict mismatch')
            checked.append({'case':path.parent.name,'decision':actual['decision']})
        if len(checked)!=len(report['cases']): raise ValueError('missing exported case evidence')
        if report['decision']=='accept_for_review' and (len(checked)!=report['tests_run'] or
                report['failures'] or report['errors'] or report['skipped'] or
                any(c['decision']!='accept_for_review' for c in checked)):
            raise ValueError('incomplete acceptance evidence')
        print(json.dumps({'verified_cases':len(checked),'tests_without_case_export':report['tests_run']-len(checked),
                          'archive_sha256':expected,'cases':checked}))

if __name__=='__main__': main()
