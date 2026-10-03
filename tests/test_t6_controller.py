"""Variant boundaries and incident-specific planning checks, no inference."""
import json
import unittest
from unittest.mock import patch
from tests.test_t4 import T4Tests
from incidentforge.controller import Controller
from incidentforge.evidence import Evidence,verify
from incidentforge.budget import Budget

class VariantTests(unittest.TestCase):
    setUp=T4Tests.setUp
    def test_evidence_unicode_verification_uses_utf8(self):
        e=Evidence(self.root/'unicode','r');e.event('claim',{'text':'compensation → release; café'})
        self.assertEqual(1,verify(e.root))
    def test_b1_cannot_receive_protected_feedback_during_repair(self):
        app=self.root/'candidate/fixture/app';app.mkdir(parents=True)
        for name in ('service.py','common.py','contract.py'): (app/name).write_text('x=1\n')
        (self.root/'candidate/CONTRACT.md').write_text('contract')
        (self.root/'candidate/INCIDENT.json').write_text('{}')
        class Backend:
            image='test';name='test';count=0;incident='IF-002';modes=[]
            def run(self,path,mode):
                self.count+=1;self.modes.append(mode);return {'complete':True}
        class Model:
            def call(self,messages): return '{"action":"validate"}'
        b=Backend();e=Evidence(self.root/'e','r')
        with patch('incidentforge.investigation.investigate',return_value={}):
            result=Controller('r',self.root/'candidate',e,b,Model(),Budget(self.root/'b.db',200000),variant='B1').run()
        self.assertEqual('unresolved',result['decision'])
        self.assertEqual(['developer'],b.modes)
        records=json.loads((e.root/'records.json').read_text())
        spec=next(r['data'] for r in records if r['kind']=='ExperimentSpec')
        self.assertIn('compensation',spec['intervention'])

if __name__=='__main__': unittest.main()
