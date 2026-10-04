"""Allowlisted source editing; never imports or executes candidate code on host."""
import ast
import difflib
import hashlib
from pathlib import Path
from .records import digest

EDITABLE={'fixture/app/service.py','fixture/app/common.py','fixture/app/contract.py'}
READABLE=EDITABLE|{'CONTRACT.md','INCIDENT.json','developer-tests.json'}

class EditMismatch(ValueError):
    def __init__(self,name,before,old):
        super().__init__('replacement must match exactly once; no edit applied')
        lines=before.splitlines(True)
        anchor=next((line.strip() for line in old.splitlines() if line.strip()),'')
        matches=difflib.get_close_matches(anchor,[line.strip() for line in lines],n=1,cutoff=.4)
        index=next((n for n,line in enumerate(lines) if matches and line.strip()==matches[0]),0)
        start=max(0,index-3);end=min(len(lines),index+16)
        self.context={'path':name,'exact_match_count':before.count(old),'first_line':start+1,
                      'source_excerpt':''.join(lines[start:end]),
                      'instruction':'Use a short unique verbatim old string from current source. Read the file if more context is needed. No fuzzy edit was applied.'}

class EditSyntaxError(SyntaxError):
    def __init__(self,name,before,after,error):
        super().__init__(error.msg)
        lines=after.splitlines(True);number=error.lineno or 1
        start=max(0,number-4);end=min(len(lines),number+3)
        self.context={'path':name,'line':number,'offset':error.offset,
            'proposed_first_line':start+1,'proposed_source_excerpt':''.join(lines[start:end]),
            'applied':False,'instruction':'Proposed source failed Python parsing; current file is unchanged. Preserve indentation of the enclosing block. Read current source before retrying; a comment alone is not a statement.'}

class Workspace:
    def __init__(self,root): self.root=root
    def path(self,name,edit=False):
        if name not in (EDITABLE if edit else READABLE): raise ValueError('path outside allowed bundle')
        p=self.root/name
        if any(q.is_symlink() for q in [p,*p.parents] if q!=self.root.parent): raise ValueError('symlink')
        if not p.resolve().is_relative_to(self.root.resolve()): raise ValueError('path escape')
        return p
    def read(self,name):
        if name=='developer-tests.json' and not self.path(name).exists(): return '{"assertions":[]}'
        raw=self.path(name).read_bytes()
        if len(raw)>64000: raise ValueError('source size bound')
        return raw.decode().replace('\r\n','\n')
    def revision(self):
        files=set(EDITABLE)
        if self.path('developer-tests.json').exists(): files.add('developer-tests.json')
        return digest({p:hashlib.sha256(self.path(p).read_bytes()).hexdigest() for p in sorted(files)})
    def search(self,query):
        result=[]
        for name in sorted(READABLE):
            for number,line in enumerate(self.read(name).splitlines(),1):
                if query.lower() in line.lower(): result.append({'path':name,'line':number,'text':line[:300]})
        return result[:40]
    def index(self):
        result={}
        for name in sorted(EDITABLE):
            tree=ast.parse(self.read(name))
            result[name]=[{'symbol':node.name,'line':node.lineno} for node in ast.walk(tree)
                          if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
        return result
    def replace(self,name,old,new):
        path=self.path(name,edit=True);before=self.read(name)
        if before.count(old)!=1: raise EditMismatch(name,before,old)
        after=before.replace(old,new,1)
        if after==before: raise ValueError('replacement makes no source change')
        if len(after.encode())>64000: raise ValueError('source size bound')
        try: ast.parse(after)
        except SyntaxError as exc: raise EditSyntaxError(name,before,after,exc) from exc
        path.write_text(after,encoding='utf-8')
        return ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=name,tofile=name))
