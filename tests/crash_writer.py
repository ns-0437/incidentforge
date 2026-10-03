"""A real process death, used by the portable durability acceptance tests."""
import os
from pathlib import Path
import sys

from fixture.harness.persistence.store import Session

session = Session(Path(sys.argv[1]))
session.request({"op": "begin"})
session.request({"op": "execute", "sql": "INSERT INTO charges VALUES(?,?,?,?)",
                 "params": ["crash-effect", "intent", "key", 100]})
if sys.argv[2] == "committed":
    session.request({"op": "commit"})
os._exit(23)  # No close, no finally, no simulated graceful cleanup.
