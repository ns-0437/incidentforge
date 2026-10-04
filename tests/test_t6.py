"""Development-only IF-002 reference and isolated negative controls."""
from tests.test_t2 import ContractTests
from fixture.harness.compensation import decline_restart
from fixture.harness.t2 import PORTS,read_rows
from fixture.app.common import http

class CompensationTests(ContractTests):
    def test_if002_reference_restart(self):
        w=self.world()
        result=decline_restart(w)
        self.assertEqual('CANCELLED_DECLINED',result['order']['status'])
        self.assertEqual('RELEASED',result['reservation']['result']['status'])
        self.verdict(w,'if002-reference-restart')

    def test_if002_fault_is_restart_specific(self):
        w=self.world(control='lost_compensation')
        w.submit('clean',expect='decline',customer_id='CUST-DECLINE')
        self.assertEqual('CANCELLED_DECLINED',w.observe('clean')['status'])
        self.verdict(w,'if002-fault-no-crash')
        w=self.world(control='lost_compensation')
        result=decline_restart(w)
        self.assertEqual('COMPENSATING',result['order']['status'])
        self.assertEqual('HELD',result['reservation']['result']['status'])
        self.verdict(w,'if002-fault-restart','reject_behavior',('P4',))

    def test_if002_harmful_repairs(self):
        for control,required in [('terminal_without_release',('P4',)),('double_release',('P5',))]:
            with self.subTest(control=control):
                w=self.world(control=control)
                w.submit('decline',expect='decline',customer_id='CUST-DECLINE')
                w.observe('decline')
                self.verdict(w,'if002-negative-'+control,'reject_behavior',required)

    def test_if002_release_replay_across_inventory_restart(self):
        w=self.world()
        decline_restart(w)
        w.restart('inventory')
        for _ in range(2):
            self.assertEqual(200,http(PORTS['inventory'],'POST','/reservations/rsv:decline/release',
                                      {'operation_key':'rel:decline'})[0])
        rows=read_rows(w.db('inventory'),"SELECT value FROM _state_audit WHERE key='reservation:rsv:decline'")
        import json
        releases=[r for r in rows if json.loads(r['value'])['result'].get('status')=='RELEASED']
        self.assertEqual(1,len(releases))
        w.protocol_checks.append({'name':'release replay survives restart without second release mutation','passed':True})
        self.verdict(w,'if002-release-replay')

    def test_development_trace_distinguishes_restart_return(self):
        from fixture.harness.trace_observation import observation
        for control in ('lost_compensation','reference'):
            w=self.world(control=control,trace=True)
            result=decline_restart(w)
            trace=observation(w)
            self.assertEqual(2,len(trace['processes']))
            events=trace['processes'][1]['events']
            self.assertTrue(events)
            self.assertLessEqual(len(events),128)
            self.assertFalse(trace['log_truncated'])
            if control=='lost_compensation':
                self.assertEqual('COMPENSATING',result['order']['status'])
                self.assertTrue(any(e['event']=='return' and e['source'].strip()=='return' for e in events))
                self.assertTrue(any('pending_compensations' in e['source'] for e in events))
                self.assertFalse(any('/release' in e['source'] for e in events))
            else:
                self.assertEqual('CANCELLED_DECLINED',result['order']['status'])
                self.assertTrue(any('/release' in e['source'] for e in events))
            w.close()

    def test_public_payment_assertion_detects_changed_retry_identity(self):
        from probes.run_candidate import payment_observation
        from fixture.harness.developer_tests import assess,validate_targets
        spec={'assertions':[{'name':'retry preserves operation identity','condition':'payment response loss',
                            'path':'payment_requests.distinct_charge_operation_keys','equals':1}]}
        for control,expected in [('fresh_key',False),('reference',True)]:
            with self.subTest(control=control):
                w=self.world(control=control,fault=True)
                code,_=w.submit();order=w.observe()
                observations=[payment_observation(w,code,order)]
                validate_targets(spec,observations)
                self.assertEqual(expected,assess(spec,{'observations':observations})['passed'])
                self.assertNotIn('committed_charge_count',observations[0])
                w.close()

    def test_public_stock_assertion_rejects_status_only_compensation(self):
        from probes.run_candidate import public_stock
        from fixture.harness.developer_tests import assess,validate_targets
        spec={'assertions':[{'name':'decline releases inventory','condition':'no_restart',
                            'path':'stock.A.held','equals':0}]}
        for control,expected in [('terminal_without_release',False),('reference',True)]:
            with self.subTest(control=control):
                w=self.world(control=control)
                w.submit('decline',expect='decline',customer_id='CUST-DECLINE')
                order=w.observe('decline')
                self.assertEqual('CANCELLED_DECLINED',order['status'])
                observations=[{'condition':'no_restart','order':order,'stock':public_stock()}]
                validate_targets(spec,observations)
                self.assertEqual(expected,assess(spec,{'observations':observations})['passed'])
                w.close()
