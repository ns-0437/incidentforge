"""Trusted launcher: drop privilege before exec, without threaded preexec_fn."""
import ctypes
import os
import sys

uid=int(sys.argv[1])
directory=sys.argv[2]
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(38,1,0,0,0)!=0: raise OSError('no_new_privs')
for cap in range(41):
    if libc.prctl(24,cap,0,0,0)!=0: raise OSError('capability drop')
os.setgroups([])
os.setresgid(uid,uid,uid)
os.setresuid(uid,uid,uid)
os.chdir(directory)
os.execv(sys.executable,[sys.executable,*sys.argv[3:]])
