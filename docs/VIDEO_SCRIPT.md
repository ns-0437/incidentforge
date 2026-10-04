# Demonstration recording script — target 2:45

Use the committed viewer with IF-001 v22 and IF-002 v25. Setup:
[RECORDING_HANDOFF.md](RECORDING_HANDOFF.md). This is recorded synthetic execution;
keep the recorded-replay label visible. Readable text and measured pauses matter more
than fitting extra claims. The narration is 243 words: roughly 112 seconds at
130 words per minute, leaving about 53 seconds for navigation and pauses in a
2:45 cut. This is an estimate, not measured recording duration.
[Plain narration](VIDEO_NARRATION.txt) is available for reading while recording.
Rehearse once and check the actual duration before upload.

| Time | Exact screen action | Narration |
|---|---|---|
| 0:00–0:15 | Overview; click Explore an investigation | “A payment response disappears after a charge commits. Retrying with a new key can charge twice. IncidentForge investigates the incident and returns a patch with evidence for human review.” |
| 0:15–0:35 | IF-001 selected, 01 Observe | “This is recorded synthetic execution. Reusing a key produced one committed charge across retries and restart. Different keys produced two. Successful HTTP responses alone cannot establish payment safety.” |
| 0:35–0:50 | 02 Investigate | “Nemotron proposes competing explanations through Nebius Token Factory. The controller checks measured facts separately. The model's causal explanation remains a claim, not a verified conclusion.” |
| 0:50–1:10 | 03 Repair; show authored checks; 04 Verify | “The repair preserves payment identity. Independent protected checks accepted it. Its authored retry-count test also passed before repair, so we disclose that it does not detect the original defect.” |
| 1:10–1:40 | Select IF-002; 01 Observe, then 03 Repair; scroll to authored checks; 04 Verify | “The second incident strands compensation after restart. The agent removes a process-local guard. Its restart assertion fails before repair and passes afterward. All eight protected cases pass. This is one successful development run after retained failures.” |
| 1:40–2:00 | Architecture navigation; select broker, then restricted reader | “The model edits an allowlisted bundle. Sandbox services run under separate identities. A protected broker records transactional effects, and an independent reader checks the returned evidence. The model cannot choose its own verdict.” |
| 2:00–2:25 | Evaluation navigation; expand Inspect every launched attempt | “The frozen comparison preserves all twelve attempts: two accepted final repairs, two rejected candidates and eight unresolved. Three inference timeouts invalidate variant ranking. Later development examples do not replace those results.” |
| 2:25–2:45 | Investigation navigation; Download evidence; finish on the desk | “A clean checkout passed 115 portable and nineteen Linux checks. This viewer is free to explore and does not call the model. IncidentForge makes the patch, tested conditions and remaining uncertainty inspectable.” |

The narration is a draft, not a recorded video. Keep the finished video strictly
under three minutes. If judge execution access is verified before recording, add
one short accurate sentence about that path without exceeding the limit. Never
imply that the Pages replay runs the agent or that checks prove universal safety.
Do not show API keys, account settings, raw prompts or unrelated windows.

## Recording acceptance

- Both incidents, the source diff, IF-002 before/after assertion and protected result are legible.
- IF-001's weak assertion and the frozen unsuccessful attempts are disclosed.
- Recorded-replay label is visible; no implication of a live run or public deployment.
- Audio is clear, actual duration is under three minutes, and no credentials appear.
- After owner upload, public YouTube playback is checked signed out.

If the final source or curated evidence changes, verify this script against the
new build before recording. The planned Pages URL is not a deployed link yet.
