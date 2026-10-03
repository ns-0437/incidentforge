"""Bounded source-mapped diagnostics; candidate process output is untrusted."""
import hashlib
import json
from .trace_runtime import PREFIX, LIMIT

def observation(world):
    source = (world.bundle/'fixture/app/service.py').read_bytes()
    lines = source.decode().splitlines()
    with (world.root/'order-service.log').open('rb') as stream: raw = stream.read(131073)
    rows = []
    pids = [item['pid'] for item in world.started_ids if item['service'] == 'order']
    for pid in pids:
        events = []; seen = set()
        for line in raw[:131072].decode(errors='replace').splitlines():
            if not line.startswith(PREFIX): continue
            try: item = json.loads(line[len(PREFIX):])
            except ValueError: continue
            if not isinstance(item, dict) or item.get('pid') != pid: continue
            number = item.get('line'); event = item.get('event')
            if type(number) is not int or not 1 <= number <= len(lines) or event not in ('line','return'): continue
            key = (event, number)
            if key in seen or len(events) >= LIMIT: continue
            seen.add(key); events.append({'event': event, 'line': number, 'source': lines[number-1]})
        rows.append({'generation': len(rows), 'events': events, 'event_limit_reached': len(events) == LIMIT})
    return {'source_path': 'fixture/app/service.py', 'source_sha256': hashlib.sha256(source).hexdigest(),
            'function': 'step', 'processes': rows, 'log_truncated': len(raw)>131072,
            'scope': 'First-seen unique line/return events per process, not a complete chronological trace. No locals captured.',
            'trust': 'Candidate-process diagnostics can be spoofed or disabled. Not protected evidence or proof of causality. Generation 0 is initial process; later generations are restarts.'}
