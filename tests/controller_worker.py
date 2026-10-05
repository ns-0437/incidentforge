"""Run the real Controller as an operator subprocess. Test-only, never a product path.

Only the two external boundaries are simulated: the model and the execution
backend. Everything between them is production code. The bundle is built the way
scripts/run-t4.py builds it, from the real fixture sources with the authored
lost_compensation control applied, so Workspace, Evidence, the investigation
schema and validator, the edit/compile gates, the authored-regression gate, the
B2 feedback limit and the final verification all execute for real.

This is a deterministic integration double. It makes no claim about live model
reliability and performs no Sandbox execution.
"""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'src'), str(REPO)]

from evaluation.controls import mutate
from incidentforge.budget import Budget
from incidentforge.controller import Controller
from incidentforge.evidence import Evidence

# The guard the lost_compensation control injects; removing it is the repair.
DEFECT = "        if phase=='COMPENSATING' and o['order_id'] not in self.pending_compensations:"
REPAIR = "        if False:  # repaired: compensation resumes after restart"


def accepted_receipt():
    """Same shape tests/test_reliability.py uses for a clean protected run."""
    return {'complete': True, 'decision': 'accept_for_review', 'tests_run': 1,
            'errors': 0, 'failures': 0, 'skipped': 0,
            'cases': [{'case': 'scripted-case', 'decision': 'accept_for_review',
                       'boundary': {'scripted-isolation-check': True},
                       'properties': {'P%d' % i: {'status': 'pass'} for i in range(1, 8)}}]}


def rejected_receipt():
    """A declared property fails, so the final verdict must be a rejection."""
    receipt = accepted_receipt()
    case = dict(receipt['cases'][0])
    properties = dict(case['properties'])
    properties['P4'] = {'status': 'fail', 'reasons': ['scripted declared property failure']}
    case['properties'] = properties
    case['decision'] = 'reject_behavior'
    return {**receipt, 'decision': 'reject_behavior', 'cases': [case]}


def investigation_from_schema(response_format):
    """Answer the provider schema the real investigator supplied, nothing more."""
    schema = response_format['json_schema']['schema']['properties']
    hypothesis_fields = schema['hypotheses']['items']['properties']
    symbol = hypothesis_fields['symbols']['items']['enum'][0]
    reference = hypothesis_fields['supporting_refs']['items']['enum'][0]
    intervention = hypothesis_fields['distinguishing_experiment']['enum'][0]

    def hypothesis(label):
        return {'mechanism': label + ' candidate mechanism', 'symbols': [symbol],
                'supporting_refs': [reference], 'counterevidence': ['scripted counterevidence'],
                'alternatives': ['scripted alternative'], 'predicted_signatures': ['scripted signature'],
                'distinguishing_experiment': intervention,
                'confidence_basis': 'scripted integration double'}

    experiment = schema['experiment']['properties']
    conditions = list(experiment['predictions']['properties'])
    predictions = {}
    for index, condition in enumerate(conditions):
        # At least one condition must distinguish the two hypotheses.
        predictions[condition] = {'H1': 'retains compensation',
                                  'H2': 'strands compensation' if index == 0 else 'retains compensation'}
    return {'hypotheses': [hypothesis('first'), hypothesis('second')],
            'experiment': {'question': 'does compensation survive a restart',
                           'baseline': 'clean reference revision', 'reset': 'fresh state per condition',
                           'intervention': experiment['intervention']['enum'][0],
                           'controlled_variables': ['restart timing'], 'workload': 'scripted workload',
                           'predictions': predictions, 'repetitions': 1,
                           'reason': 'separates the two mechanisms', 'limits': {'seconds': 30}}}


class ScriptedModel:
    def __init__(self, candidate):
        self.candidate = candidate
        self.actions = None
        self.calls = 0

    def script(self):
        source = (self.candidate / 'fixture/app/service.py').read_text(encoding='utf-8')
        if source.count(DEFECT) != 1:
            raise RuntimeError('expected exactly one lost_compensation guard to repair')
        return [
            lambda payload: json.dumps(payload['action_contract']['interpret_fields']),
            {'action': 'replace', 'path': 'fixture/app/service.py', 'old': DEFECT, 'new': REPAIR,
             'reason': 'restore compensation after restart'},
            {'action': 'developer_test',
             'spec': {'assertions': [{'name': 'order completes', 'condition': 'clean',
                                      'path': 'order.status', 'equals': 'CONFIRMED'}]},
             'reason': 'regression for the repaired path'},
            {'action': 'test'},
            {'action': 'validate'},
            {'action': 'finish', 'summary': 'compensation guard removed; authored regression executed'},
        ]

    def call(self, messages, response_format=None, **kwargs):
        self.calls += 1
        # Only the investigation turn carries the hypotheses schema. Other turns
        # may also supply a response_format, so match on the schema itself.
        schema = ((response_format or {}).get('json_schema') or {}).get('schema') or {}
        if 'hypotheses' in (schema.get('properties') or {}):
            return json.dumps(investigation_from_schema(response_format))
        payload = json.loads(messages[-1]['content'])
        if self.actions is None:
            self.actions = iter(self.script())
        command = next(self.actions)
        return command(payload) if callable(command) else json.dumps(command)


# Condition names are fixed by src/incidentforge/investigation.py per incident.
EXPERIMENT_OBSERVATIONS = {
    'compensation_probe': [
        {'condition': 'no_restart', 'order': {'status': 'CANCELLED_DECLINED'}},
        {'condition': 'order_restart', 'order': {'status': 'COMPENSATING'}},
        {'condition': 'release_replay', 'order': {'status': 'CANCELLED_DECLINED'}},
        {'condition': 'release_replay_inventory_restart', 'order': {'status': 'CANCELLED_DECLINED'}},
    ],
    'identity_probe': [
        {'condition': 'same_key_sequential', 'committed_charge_count': 1},
        {'condition': 'same_key_restart', 'committed_charge_count': 1},
        {'condition': 'same_key_concurrent', 'committed_charge_count': 1},
        {'condition': 'different_keys', 'committed_charge_count': 2},
    ],
}


class ScriptedBackend:
    name = 'test-scripted-backend'
    image = 'test-image'

    def __init__(self, incident, final_rejects):
        self.incident = incident
        self.final_rejects = final_rejects
        self.count = 0
        self.protected = 0
        self.modes = []

    def run(self, path, mode):
        self.count += 1
        self.modes.append(mode)
        if mode == 'protected':
            self.protected += 1
            # First protected run is the B2 development feedback; the last is the
            # independent final verification after freeze.
            if self.final_rejects and self.protected >= 2:
                return rejected_receipt()
            return accepted_receipt()
        if mode in ('compensation_probe', 'identity_probe'):
            # The distinguishing experiment must observe every declared condition
            # exactly once, as src/incidentforge/grounding.py requires.
            return {**accepted_receipt(), 'observations': EXPERIMENT_OBSERVATIONS[mode]}
        result = {**accepted_receipt(),
                  'observations': [{'condition': 'clean', 'order': {'status': 'CONFIRMED'}}]}
        if mode == 'developer':
            from fixture.harness.developer_tests import execute
            result['developer_tests'] = execute(path / 'developer-tests.json', result)
        return result


def build_bundle(candidate, incident):
    """The same bundle layout scripts/run-t4.py prepares."""
    app = candidate / 'fixture/app'
    app.mkdir(parents=True)
    for name in ('common.py', 'contract.py'):
        (app / name).write_bytes((REPO / 'fixture/app' / name).read_bytes())
    control = 'fresh_key' if incident == 'IF-001' else 'lost_compensation'
    (app / 'service.py').write_text(mutate((REPO / 'fixture/app/service_v2.py').read_text(), control))
    (candidate / 'CONTRACT.md').write_bytes((REPO / 'contracts/public/CONTRACT.md').read_bytes())
    (candidate / 'INCIDENT.json').write_text(json.dumps({
        'incident_id': incident,
        'symptom': 'A declined order leaves stock reserved after service restart.',
        'services': ['Order', 'Inventory', 'Payment'],
        'visible_tests': 'declared development observations'}))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--control', required=True, type=Path)
    parser.add_argument('--incident', default='IF-002')
    parser.add_argument('--variant', default='B2')
    parser.add_argument('--final', choices=('accept', 'reject'), default='accept')
    args = parser.parse_args(argv)

    evidence = Evidence(args.root / 'runs' / args.run_id, args.run_id)
    candidate = evidence.root / 'candidate'
    build_bundle(candidate, args.incident)
    (args.control / 'ready').write_text(args.run_id, encoding='utf-8')

    budget = Budget.existing(args.root / 'runs/t4-budget.sqlite')
    backend = ScriptedBackend(args.incident, args.final == 'reject')
    model = ScriptedModel(candidate)
    cancel = evidence.root / 'CANCEL'
    report = Controller(args.run_id, candidate, evidence, backend, model, budget,
                        cancel, variant=args.variant).run()
    (args.control / 'exited').write_text(str(report.get('decision')), encoding='utf-8')
    return 0 if report['decision'] == 'accept_for_review' else 1


if __name__ == '__main__':
    raise SystemExit(main())
