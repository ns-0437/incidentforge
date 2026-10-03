# IncidentForge judge guide

## Start with the recorded evidence

Open https://ns-0437.github.io/incidentforge-demo/. This is a static recorded replay,
not a hosted inference service. It cannot spend credits or launch a sandbox.

Select IF-001 for duplicate payment after a lost response, or IF-002 for stranded
compensation after restart. Follow Observe, Investigate, Repair and Verify. Model
hypotheses remain unverified claims. The architecture diagram explains who may
edit source and who independently evaluates effects. Download the curated JSON
to inspect the displayed observations.

The Evaluation section discloses every T8 attempt: twelve launches, two accepted
final repairs, two rejected candidates and eight unresolved attempts. Three
inference timeouts invalidate variant ranking. Successful development replays
are not the benchmark score. Later reliability pilots remain separate.

## Run the test build

Use Python 3.12 or newer and Docker Desktop with Linux containers. The source
repository is https://github.com/ns-0437/incidentforge; it remains private during
development and must become public before submission. Do not claim this guide
provides judge access until that release step is complete.

```powershell
git clone https://github.com/ns-0437/incidentforge.git
cd incidentforge
python -m unittest tests.test_t4 tests.test_t5 tests.test_t6_controller tests.test_t7 tests.test_prefreeze tests.test_t8 tests.test_reliability
python scripts/serve-ui.py --port 8765
```

Visit http://127.0.0.1:8765. A fresh checkout has empty run history; raw local runs
are intentionally excluded from Git. The public replay supplies curated examples.
The controller and portable tests use the Python standard library.

For Linux behavioral/isolation checks, in another terminal:

```powershell
docker image inspect python:3.12-slim
# Only if the image is absent:
docker pull python:3.12-slim
.\scripts\run-t0-linux.ps1 -Stage t6
```

These checks use authored controls, not live model inference. Scripts remove only
their own disposable container and volume. Do not use a global Docker prune.

## Live execution — access must be arranged before submission

Nebius Sandbox beta access, a Token Factory account and funded model access are
required. The existing operator profile is already authenticated. Do not paste
keys into issue trackers, the public frontend, screenshots or source files.
Set `CONTREE_PYTHON` to the installed ConTree SDK Python if it differs from the
Windows default. Docker independently checks returned protected evidence.

```powershell
python scripts/run-t4.py --live --variant B2 --incident IF-001 --backend contree
```

The local UI launches Docker; the command above uses real Nebius Sandbox. The
persisted budget blocks dispatch that is not funded or has unknown pending usage.
Never delete the ledger or start a fresh one to evade the project allocation.
The current development allocation cannot fund another call. Judge credentials
and funding through December 15 are not yet confirmed; do not require judges to
purchase credits. The public replay does not resolve this access requirement.

## Inspect results honestly

`accept_for_review` means the declared finite checks accepted a candidate, not
universal correctness or production deployment. `unresolved` means the agent
did not complete. Passing intermediate protected feedback or a later manual
diagnostic does not change an unresolved run into a successful autonomous run.

See T8_RESULTS.md for the comparison, POST_T8_RELIABILITY.md for subsequent
changes, and benchmarks/ for sanitized results. Frozen T8 reproduction requires
the recorded historical revision rather than current development source.
