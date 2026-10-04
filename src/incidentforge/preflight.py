"""Read-only readiness checks. Never dispatch inference or Sandbox operations."""
import os
from pathlib import Path
import subprocess
import sys
from .llm import credential,CALL_RESERVATION
from .remote_backend import reader_preflight
from .ui import budget_status


def inspect(root,backend='contree'):
    if backend not in ('docker','contree'): raise ValueError('Unsupported backend')
    checks=[]
    def add(name,ready,detail): checks.append({'check':name,'ready':bool(ready),'detail':detail})
    add('python',sys.version_info>=(3,12),'Python 3.12 or newer required')
    try:
        image=reader_preflight()
        add('verifier',True,image)
    except RuntimeError as exc: add('verifier',False,str(exc))
    try:
        available=bool(credential())
    except Exception: available=False
    add('inference_credential',available,'Credential present locally; validity and funding are not checked' if available else 'Set NEBIUS_API_KEY locally or authenticate ConTree; never paste a key into this report')
    try:
        budget=budget_status(root)
        ready=budget['pending']==0 and budget['remaining_usd']>=CALL_RESERVATION/1e6
        add('allocation',ready,{'ledger_exists':(root/'runs/t4-budget.sqlite').exists(),**budget})
    except Exception:
        add('allocation',False,'Ledger unreadable; inspect it without deleting or resetting it')
    add('local_launch',not (root/'runs/ui-launches/active.json').exists(),'An existing launch guard requires terminal-state reconciliation')
    if backend=='contree':
        runtime=Path(os.environ.get('CONTREE_PYTHON',str(Path.home()/'AppData/Roaming/uv/tools/contree-cli/Scripts/python.exe')))
        installed=False
        if runtime.is_file():
            try:
                result=subprocess.run([str(runtime),'-c','import contree_client'],capture_output=True,timeout=15,
                                      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                installed=result.returncode==0
            except (OSError,subprocess.SubprocessError): pass
        add('sandbox_sdk',installed,'CONTREE_PYTHON must point to Python with contree_client installed')
        add('sandbox_operation',not (root/'runs/contree-active.json').exists(),'An existing remote guard requires terminal-state reconciliation')
    return {'backend':backend,'ready_for_preflighted_launch':all(c['ready'] for c in checks),'checks':checks,
            'limitations':['Local checks only; no provider authentication, credit, expiry or judge-access confirmation.',
                           'An absent ledger uses the default $0.20 allocation on first launch; this does not supply provider credits.',
                           'No inference or Sandbox call was made; dependencies can become unavailable after this check.']}
