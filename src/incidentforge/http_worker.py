"""One HTTP request in a killable host process; never runs candidate code."""
import json
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from incidentforge.llm import credential,ENDPOINT,REQUEST_SECONDS

def main():
    try:
        payload=sys.stdin.buffer.read(110001)
        if len(payload)>110000: raise ValueError('payload bound')
        request=urllib.request.Request(ENDPOINT,data=payload,method='POST',
            headers={'Authorization':'Bearer '+credential(),'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=REQUEST_SECONDS) as response: raw=response.read(1_000_001)
        if len(raw)>1_000_000: raise ValueError('response bound')
        sys.stdout.buffer.write(raw)
        return 0
    except Exception as exc:
        # Never serialize exceptions that could contain request headers.
        sys.stderr.write(type(exc).__name__)
        return 1

if __name__=='__main__': raise SystemExit(main())
