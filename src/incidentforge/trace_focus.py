"""Compact candidate diagnostics, bound to exact source bytes; never a verdict."""
import hashlib

def focus(observations, source):
    expected = hashlib.sha256(source).hexdigest()
    lines = source.decode().splitlines()
    rows = []
    for item in observations[:12]:
        trace = item.get('execution_trace')
        if not isinstance(trace, dict): continue
        condition = item.get('condition', item.get('fault'))
        matched = trace.get('source_sha256') == expected
        row = {'condition': condition, 'source_matches': matched,
               'log_truncated': bool(trace.get('log_truncated')), 'processes': []}
        if matched:
            for process in trace.get('processes', [])[:4]:
                returns = []; seen = set()
                for event in process.get('events', [])[:128]:
                    number = event.get('line')
                    if event.get('event') != 'return' or type(number) is not int or not 1 <= number <= len(lines): continue
                    if number in seen: continue
                    seen.add(number)
                    if len(returns) >= 8: break
                    lo, hi = max(1, number-4), min(len(lines), number+2)
                    returns.append({'line': number, 'context': [
                        {'line': n, 'source': lines[n-1]} for n in range(lo, hi+1)]})
                row['processes'].append({'generation': process.get('generation'),
                    'event_limit_reached': bool(process.get('event_limit_reached')),
                    'observed_returns': returns})
        rows.append(row)
    return {'conditions': rows,
            'trust': 'Untrusted candidate-process diagnostics. Source mapping checked, execution not independently attested.',
            'interpretation': 'Conditions are independent. Generations are separate processes. Return contexts are executed return locations, not proof of cause. Empty lists or absent lines do not prove non-execution. Mismatched source suppresses stale locations.'}
