import json
import unittest
from unittest.mock import patch
from tests import test_t4
from incidentforge.investigation import feedback,validate_plan
from incidentforge.records import action
from incidentforge.controller import Controller
from incidentforge.budget import Budget
from incidentforge.evidence import Evidence

class T5Tests(unittest.TestCase):
    def test_feedback_excludes_private_details(self):
        result=feedback({'complete':True,'decision':'reject_behavior','secret':'hidden',
            'cases':[{'case':'private schedule','properties':{'P1':{'status':'fail','reason':'secret'},
            'P2':{'status':'pass'}},'path':'private'}]})
        self.assertEqual(['P1'],result['failed_properties'])
        self.assertNotIn('secret',json.dumps(result))
        self.assertNotIn('private',json.dumps(result))

    def test_interpretation_requires_nonempty_fields(self):
        with self.assertRaises(ValueError): action(json.dumps({'action':'interpret','conclusion':'',
            'supported':'a','weakened':'b','uncertainty':'c'}))
        with self.assertRaises(ValueError): validate_plan({'hypotheses':[],'experiment':{}})

class GateTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp
    def test_b2_refuses_patch_before_interpretation(self):
        app=self.root/'candidate/fixture/app';app.mkdir(parents=True)
        for name in ('service.py','common.py','contract.py'): (app/name).write_text('x=1\n')
        (self.root/'candidate/CONTRACT.md').write_text('contract')
        (self.root/'candidate/INCIDENT.json').write_text('{}')
        class Backend:
            image='test';name='test-double';count=0
            def run(self,path,mode):
                self.count+=1
                return {'complete':True}
        class Model:
            def call(self,messages):
                return json.dumps({'action':'replace','path':'fixture/app/service.py',
                    'old':'x=1','new':'x=2','reason':'unsupported guess'})
        e=Evidence(self.root/'e','r')
        with patch('incidentforge.investigation.investigate',return_value={'measured_result':'test'}):
            result=Controller('r',self.root/'candidate',e,Backend(),Model(),
                Budget(self.root/'b.db',200000),variant='B2').run()
        self.assertEqual('unresolved',result['decision'])
        self.assertEqual(0,result['edits'])
        self.assertEqual('x=1\n',(app/'service.py').read_text())

if __name__=='__main__': unittest.main()
