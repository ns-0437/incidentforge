"""Bounded archive/hash/database verification; run in a network-disabled reader."""
from contextlib import closing
import hashlib
import json
from pathlib import Path,PurePosixPath
import sqlite3
import stat
import sys
import tempfile
import time
import zipfile


def unpack(archive,destination):
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        if len(entries)>512 or sum(i.file_size for i in entries)>16_000_000:
            raise ValueError('archive exceeds bound')
        seen=set()
        for info in entries:
            p=PurePosixPath(info.filename)
            if (p.is_absolute() or '..' in p.parts or '\\' in info.filename or ':' in info.filename
                    or not p.parts or info.filename in seen or info.file_size>4_000_000
                    or stat.S_ISLNK(info.external_attr>>16)):
                raise ValueError('invalid archive member')
            seen.add(info.filename)
            target=destination.joinpath(*p.parts)
            if not target.resolve().is_relative_to(destination.resolve()): raise ValueError('path escape')
            target.parent.mkdir(parents=True,exist_ok=True)
            if info.is_dir(): target.mkdir(exist_ok=True)
            else: target.write_bytes(z.read(info))


def verify(archive,expected):
    actual=hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual!=expected: raise ValueError('archive digest mismatch')
    with tempfile.TemporaryDirectory(prefix='if-reader-') as tmp:
        root=Path(tmp)
        unpack(archive,root)
        report=json.loads((root/'t2/report.json').read_text())
        if report['status']!='PASS' or report['failures'] or report['errors'] or report['skipped']:
            raise ValueError('remote acceptance did not pass')
        checked=0
        decisions=[]
        for p in sorted((root/'t2').glob('*/manifest.json')):
            manifest=json.loads(p.read_text())
            validation=json.loads((p.parent/'validation.json').read_text())
            if hashlib.sha256(p.read_bytes()).hexdigest()!=validation['manifest_sha256']:
                raise ValueError('manifest mismatch')
            if not validation['boundary'] or not all(validation['boundary'].values()):
                raise ValueError('boundary check failed')
            for service in ('order','inventory','payment'):
                db=p.parent/(service+'.db')
                if hashlib.sha256(db.read_bytes()).hexdigest()!=manifest['snapshots'][service]['sha256']:
                    raise ValueError('database digest mismatch')
                with closing(sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)) as conn:
                    deadline=time.monotonic()+2
                    conn.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
                    if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('database integrity')
                checked+=1
            decisions.append({'name':p.parent.name,'decision':validation['decision']})
        if len(decisions)!=len(report['cases']): raise ValueError('case export incomplete')
        return {'status':'PASS','tests_run':report['tests_run'],'failures':report['failures'],
            'errors':report['errors'],'skipped':report['skipped'],'cases':decisions,
            'verified_database_backups':checked,'archive_sha256':actual,
            'suite_duration_seconds':report['duration_seconds'],'python':report['python'],'platform':report['platform']}


if __name__=='__main__':
    print(json.dumps(verify(Path(sys.argv[1]),sys.argv[2]),indent=2))
