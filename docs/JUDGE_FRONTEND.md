# Judge frontend release plan

Owner selected main-repository GitHub Pages at release on October 4.
The existing About link is retained as requested; it returned 404 on October 4.
The intended replacement URL is https://ns-0437.github.io/incidentforge/.
It is not deployed yet. The main repository remains private.

## Prepared deployment

The manual `Publish judge frontend` workflow publishes only `site/` and runs only
for the public main repository on its main branch. No push automatically deploys.
`scripts/check-site.py` requires the exact seven curated files, rejects symlinks
and extra files, and verifies the evidence hash before upload. It is not a secret
scanner or a substitute for reviewing newly curated evidence.

At the owner-approved source release:

1. Review and publish the main repository.
2. In Settings > Pages, choose GitHub Actions as the publishing source.
3. Run `Publish judge frontend` on main and confirm deployment succeeds.
4. Open the new URL signed out; check both incidents, tabs, architecture,
   evidence download, and the disclosed failed attempts.
5. After successful deployment, update the About website, README, recording
   handoff and Devpost draft to the new URL. Do not recreate the separate demo repo.

For local recording before release:
`python -m http.server 8766 --bind 127.0.0.1 --directory site`
Open http://127.0.0.1:8766. No inference is used by the replay.

The site displays recorded synthetic evidence; it cannot start investigations.
Working judge execution access remains a separate requirement awaiting the Nebius
reply and a concrete access rehearsal. A passing Pages deployment does not close it.

Workflow reference checked October 4:
https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Clean checkout and evidence provenance

The seven files in `site/` are committed release artifacts. A clean checkout can
verify them with `python scripts/check-site.py` and serve them using the command
above; it does not need an API key, SDK, account balance, or local run history.
The publishing check also rejects inconsistent property coverage and campaign counts.

`scripts/build-judge-data.py` is the maintainer's export tool. It intentionally
requires the original local runs, which are excluded from Git to avoid publishing
raw prompts and environment details. Judges should use the committed curated data;
rebuilding that data from raw runs is not part of the clean-checkout quick start.
Its SHA256 detects changes to the curated artifact, not independent attestation of
historical execution. Sanitized pilot receipts identify runs and retained archive
hashes. The live workflow creates a new evidence chain for its own execution.
