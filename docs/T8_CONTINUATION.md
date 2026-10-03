# T8 accounting amendment — 2026-10-03

Authorized by the user's request to complete T8 after the explicit proposal to
count unknown inference usage at its full reservation against the $0.20 cap.

Slots 1–4 remain unchanged. Only unlaunched slots 5–12 may run. The original
freeze, source pins, prompts, model settings, schedule, evaluator and per-run
bounds remain unchanged. No failed attempt is retried or replaced.

For a completed T8 attempt reporting unknown inference usage, retain `actual`
as NULL and the full 17,695 micro-USD reservation in the project exposure. Mark
the reservation `conservative_unknown`, and record the accounting authorization
in a separate audit table. This is a conservative budget allocation, not a claim
of provider usage. The previous report and event chain remain untouched.

The continuation driver checks original source/driver hashes, skips completed
launches, refuses incomplete launches, and preserves remote-operation guards.
New unknown calls from completed attempts receive the same conservative treatment.
Insufficient remaining funds or an unresolved remote operation still stops work.

This is a disclosed operational amendment after observing four failed attempts.
Report all twelve planned slots, all unknown usage and the interruption; do not
present the campaign as uninterrupted or claim statistical superiority.
