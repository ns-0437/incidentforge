"""Compact candidate diagnostics, bound to exact source bytes; never a verdict."""
import hashlib
import ast

def focus(observations, source):
    expected = hashlib.sha256(source).hexdigest()
    lines = source.decode().splitlines()
    tree = ast.parse(source.decode())
    attributes = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                  and isinstance(n.value, ast.Name) and n.value.id == 'self']
    def guard_context(number):
        guards = [n for n in ast.walk(tree) if isinstance(n, ast.If)
                  and n.lineno <= number <= n.end_lineno
                  and any(isinstance(r, ast.Return) and r.lineno == number for r in ast.walk(n))]
        out = []
        for guard in sorted(guards, key=lambda n: n.end_lineno-n.lineno)[:3]:
            names = sorted({n.attr for n in ast.walk(guard.test) if isinstance(n, ast.Attribute)
                            and isinstance(n.value, ast.Name) and n.value.id == 'self'})[:6]
            out.append({'guard_line': guard.lineno, 'guard_source': lines[guard.lineno-1],
                'attribute_references': [{'attribute': 'self.'+name,
                    'source_references': [{'line': i, 'source': lines[i-1]}
                        for i in sorted({n.lineno for n in attributes if n.attr == name})[:12]]}
                    for name in names]})
        return out
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
                    returns.append({'line': number, 'enclosing_guards': guard_context(number), 'context': [
                        {'line': n, 'source': lines[n-1]} for n in range(lo, hi+1)]})
                row['processes'].append({'generation': process.get('generation'),
                    'event_limit_reached': bool(process.get('event_limit_reached')),
                    'observed_returns': returns})
        rows.append(row)
    return {'conditions': rows,
            'static_scope': 'Guard and attribute references are syntax-only links, not proof of persistence, data flow or causality.',
            'trust': 'Untrusted candidate-process diagnostics. Source mapping checked, execution not independently attested.',
            'interpretation': 'Conditions are independent. Generations are separate processes. Return contexts are executed return locations, not proof of cause. Empty lists or absent lines do not prove non-execution. Mismatched source suppresses stale locations.'}
