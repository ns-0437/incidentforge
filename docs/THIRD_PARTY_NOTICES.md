# Third-party services and runtime notices

Reviewed October 3, 2026. IncidentForge source is licensed under the repository's
MIT license. That license does not relicense third-party models or services.

## NVIDIA model

The runtime endpoint is `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` on Nebius Token
Factory. NVIDIA's [published model repository](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/tree/main)
identifies the model license as `nvidia-nemotron-open-model-license`.
Consult the license supplied by NVIDIA for its governing terms. The hosted alias
does not pin the provider's exact weight revision or precision. This project
calls the hosted endpoint; it does not redistribute model weights.

## Runtime and services

The controller and portable tests use Python's standard library; `pyproject.toml`
declares no third-party Python application dependencies. Python, SQLite, Docker,
the `python:3.12-slim` image and the externally installed ConTree CLI/SDK retain
their own licenses and terms. Runtime image IDs are recorded with executions;
these images and external SDKs are not bundled as repository source.
Nebius Token Factory and Sandbox access remain subject to their service terms.
The recorded static demonstration is deployed from the public main repository at
https://ns-0437.github.io/incidentforge/ (verified October 25, 2026).
It does not host the live inference backend.

## Attribution and ownership review

AIOpsLab is acknowledged as prior art in the README; an acknowledgment is not
permission to copy its implementation. Claude Code and Codex assisted development.
Before final submission, the owner must confirm the authorship and reuse disclosure
in the submission draft and review any assets added for the final video.
This inventory is not a claim that model terms are identical to the MIT license.
