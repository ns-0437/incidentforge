"""Allowlisted source editing; never imports or executes candidate code on host."""
import ast
import difflib
import hashlib
from pathlib import Path
import sys
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
            'applied':False,'instruction':'Proposed source failed Python compilation; current file is unchanged. Preserve indentation of the enclosing block. Read current source before retrying; a comment alone is not a statement.'}

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
    def imports(self,name):
        """Deterministic AST import records for one allowlisted file.

        Static text only: an import says a module is referenced, not that any call
        happened at runtime, and never that one service called another over HTTP.
        `level` is the relative-import depth, 0 for absolute imports.
        """
        records=[]
        for node in ast.walk(ast.parse(self.read(name))):
            if isinstance(node,ast.Import):
                for alias in node.names:
                    records.append({'module':alias.name,'name':None,'alias':alias.asname,
                                    'level':0,'line':node.lineno})
            elif isinstance(node,ast.ImportFrom):
                for alias in node.names:
                    records.append({'module':node.module,'name':alias.name,'alias':alias.asname,
                                    'level':node.level,'line':node.lineno})
        return sorted(records,key=lambda r:(r['line'],str(r['module']),str(r['name'])))

    def index(self):
        result={}
        for name in sorted(EDITABLE):
            tree=ast.parse(self.read(name))
            result[name]={'symbols':[{'symbol':node.name,'line':node.lineno} for node in ast.walk(tree)
                                     if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))],
                          'imports':self.imports(name)}
        return result

    def dependency_provenance(self):
        """Measured from the allowlisted source, never declared or invented.

        Top-level modules each editable file imports, split by whether this
        interpreter reports them as standard library. Relative imports are
        recorded as internal. The interpreter that runs the fixture is the
        sandbox image's, not this host's, so no runtime version is asserted here;
        image_digest carries the identity that is actually measured.
        """
        external,standard,internal=set(),set(),set()
        for name in sorted(EDITABLE):
            for record in self.imports(name):
                if record['level']:
                    internal.add('.'*record['level']+(record['module'] or ''));continue
                top=(record['module'] or '').split('.')[0]
                if not top: continue
                (standard if top in sys.stdlib_module_names else external).add(top)
        return {'source':'ast of allowlisted fixture source','external_modules':sorted(external),
                'standard_library_modules':sorted(standard),'internal_relative_imports':sorted(internal),
                'runtime_interpreter':'not measured on the host; the fixture runs in the pinned image'}
    def replace(self,name,old,new):
        path=self.path(name,edit=True);before=self.read(name)
        if before.count(old)!=1: raise EditMismatch(name,before,old)
        after=before.replace(old,new,1)
        if after==before: raise ValueError('replacement makes no source change')
        if len(after.encode())>64000: raise ValueError('source size bound')
        try: compile(after,name,'exec')
        except SyntaxError as exc: raise EditSyntaxError(name,before,after,exc) from exc
        path.write_text(after,encoding='utf-8')
        return ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=name,tofile=name))
