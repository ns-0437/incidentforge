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
