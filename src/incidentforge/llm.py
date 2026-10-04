"""Single-request Nebius adapter; credentials remain on the host."""
import configparser
from decimal import Decimal,ROUND_CEILING
import json
import os
from pathlib import Path
import urllib.request
import time
import subprocess
import sys
from .records import encoded

MODEL='nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'
ENDPOINT='https://api.tokenfactory.nebius.com/v1/chat/completions'
MAX_OUTPUT=8192
REQUEST_SECONDS=120
# Public catalog verified 2026-10-03. Reserve the entire advertised 262k
# context at input price plus maximum output, not an optimistic text estimate.
INPUT_RATE=Decimal('0.06')
OUTPUT_RATE=Decimal('0.24')
CALL_RESERVATION=int((Decimal(262144)*INPUT_RATE+MAX_OUTPUT*OUTPUT_RATE).to_integral_value(rounding=ROUND_CEILING))

def cost(prompt,completion):
    if type(prompt) is not int or type(completion) is not int or prompt<0 or completion<0:
        raise ValueError('invalid usage counters')
    return int((prompt*INPUT_RATE+completion*OUTPUT_RATE).to_integral_value(rounding=ROUND_CEILING))

def credential():
    key=os.environ.get('NEBIUS_API_KEY')
    if key: return key
    # Use the exact account already authenticated for this project. Never print
    # or place profile contents in candidate bundles, prompts or event artifacts.
    config=configparser.ConfigParser()
    config.read(Path.home()/'.config/contree/auth.ini')
    profile=config.defaults().get('profile','default')
    key=config.get('profile:'+profile,'token',fallback=None)
    if not key: raise RuntimeError('Token Factory credential not configured')
    return key

def request_once(payload):
    process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('http_worker.py'))],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        raw,error=process.communicate(encoded(payload),timeout=REQUEST_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill();process.communicate(timeout=5)
        raise TimeoutError('Inference wall-time cap; usage unknown, no retry')
    if process.returncode: raise RuntimeError('Inference request failed; usage unknown, no retry')
    if len(raw)>1_000_000: raise ValueError('response bound')
    return raw

class Nebius:
    def __init__(self,budget,run_id,evidence,cancel_file=None):
        self.budget,self.run_id,self.evidence=budget,run_id,evidence
        self.cancel_file=cancel_file

    def call(self,messages,*,response_format=None):
        if time.monotonic()+REQUEST_SECONDS+10>getattr(self,'deadline',float('inf')):
            raise TimeoutError('Insufficient controller time for bounded inference')
        if self.cancel_file and self.cancel_file.exists(): raise RuntimeError('Cancellation requested before inference dispatch')
        if len(encoded(messages))>100000: raise ValueError('prompt byte bound')
        payload={'model':MODEL,'messages':messages,'max_tokens':MAX_OUTPUT,'temperature':0.2,
                 'response_format':response_format if response_format is not None else {'type':'json_object'}}
        if len(encoded(payload))>110000: raise ValueError('payload byte bound')
        token=self.budget.reserve(self.run_id,CALL_RESERVATION,200000,10)
        self.evidence.event('model_reserved',{'reservation':token,'maximum_microusd':CALL_RESERVATION,
                            'model':MODEL,'prompt':self.evidence.artifact(messages),
                            'response_format':self.evidence.artifact(payload['response_format'])})
        # Killable wall-time bound, not just a socket inactivity timeout.
        # A timeout leaves its reservation unresolved and blocks redispatch.
        raw=request_once(payload)
        result=json.loads(raw)
        usage=result['usage']
        actual=cost(usage['prompt_tokens'],usage['completion_tokens'])
        self.budget.settle(token,actual)
        choice=result['choices'][0]
        content=choice['message'].get('content') or ''
        self.evidence.event('model_response',{'reservation':token,'response_id':result.get('id'),
            'usage':usage,'estimated_microusd':actual,'finish_reason':choice.get('finish_reason'),
            'content':self.evidence.artifact(content.encode())})
        return content
