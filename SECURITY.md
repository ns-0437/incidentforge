# Security and trust boundaries

Do not upload real customer logs, secrets or production data to this prototype.
Use synthetic fixtures. Credentials stay in environment variables or the existing
ConTree profile, never in source, candidate bundles, model prompts or evidence exports.

Candidates execute in isolated Linux processes with separate UIDs and stores,
dropped capabilities and disabled guest networking. Protected code and audit stores
remain inaccessible to candidate users. Returned databases are parsed by a separate
restricted Docker reader. This is tested boundary coverage, not a proof against
kernel exploits or every malicious program.

The UI is a loopback-only operator console. It is not a public multi-user service.
Do not expose it through a tunnel without adding authentication and deployment review.
Unknown inference usage and remote execution states block redispatch. Reconcile them;
do not delete guards to force a retry.

Report a suspected issue privately to the repository owner. Include a synthetic
reproduction and omit API keys, customer data and raw credential files.
