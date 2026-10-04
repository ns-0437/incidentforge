# Recorded frontend — public deployment retired

On October 4 the owner requested deletion of the separate demo repository and
will perform that deletion manually. The main repository About link was cleared.
Keep `site/` in the private main repository for local replay and recording:
`python -m http.server 8766 --bind 127.0.0.1 --directory site`.
Do not republish the separate repository. The following is historical deployment
documentation, not current instructions.

# Public judge frontend

Live URL: https://ns-0437.github.io/incidentforge-demo/

The public `ns-0437/incidentforge-demo` repository contains only the static site,
MIT license, and curated synthetic evidence. The main `ns-0437/incidentforge`
repository remains private. Its About website points to the deployed demo.

The site is a recorded replay, not a live controller. It makes no inference calls,
accepts no credentials, and launches no sandbox operations. IF-001 uses a recorded
local Docker run; IF-002 uses a recorded Nebius Sandbox run. Model hypotheses are
labeled unverified. All twelve T8 attempts and the infrastructure limitation are
disclosed separately from the accepted development repairs.

## Update procedure

1. Run `python scripts/build-judge-data.py` in the main repository. The exporter
   checks retained event chains and exports an explicit allowlist of fields.
2. Review `site/evidence.json` before publishing. Never copy raw runs, databases,
   private schedules, credentials, or the main repository history to the demo.
3. Copy only `.nojekyll`, `index.html`, `style.css`, `app.js`, `icon.svg`,
   `evidence.json`, and `evidence.sha256` from `site/` to the demo repository.
4. Preserve `evidence.json` bytes with `-text` in both repositories' attributes.
   Commit and push the demo. Pages deploys `main` from `/`.
5. Check Pages build success, the live page, and the downloaded evidence hash.

Local preview: `python -m http.server 8770 --bind 127.0.0.1 --directory site`.

Validation on 2026-10-03: JavaScript syntax checked; desktop (1440px) and mobile
(390px) layouts inspected; incident selection, repair and verification tabs,
attempt disclosure, and architecture controls exercised without console errors.
The evidence hash identifies this curated export; it does not independently
authenticate the original execution.
