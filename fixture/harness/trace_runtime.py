"""Bounded candidate-process diagnostics; never protected verification evidence."""
import json
import os
from pathlib import Path
import runpy
import sys
import threading
PREFIX = 'IF_TRACE_V1 '
LIMIT = 128
class Recorder:
    def __init__(self, target, emit):
        self.target = os.path.normcase(os.path.realpath(target))
        self.emit = emit
        self.seen = set()
        self.lock = threading.Lock()
    def trace(self, frame, event, arg):
        if frame.f_code.co_name != 'step' or os.path.normcase(os.path.realpath(frame.f_code.co_filename)) != self.target: return None
        if event in ('line', 'return'):
            key = (event, frame.f_lineno)
            with self.lock:
                if key not in self.seen and len(self.seen) < LIMIT:
                    self.seen.add(key)
                    self.emit({'pid': os.getpid(), 'event': event, 'line': frame.f_lineno})
        return self.trace

def main():
    recorder = Recorder(Path('fixture/app/service.py'), lambda item: print(PREFIX + json.dumps(item), flush=True))
    sys.settrace(recorder.trace)
    threading.settrace(recorder.trace)
    runpy.run_module('fixture.app.service', run_name='__main__')
if __name__ == '__main__': main()
