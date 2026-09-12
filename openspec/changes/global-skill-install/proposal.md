## Why

The OpenSpec workflow skills (`openspec-propose`, `openspec-apply-change`, …) were installed **per project** by `openspec init --tools agents` into this repository's `.agents/skills/`, so they only appear in sessions whose workspace is this repo. The user wants the OpenSpec workflow usable in **every DeepSeek Harness standard mode/session**, regardless of which workspace is open. DeepSeek Harness discovers skills from project roots (`.dsh/skills`, `.agents/skills`) *and* user-global roots (`~/.dsh/skills`, `~/.agents/skills`), so the fix is to install the skills into the global root as well.

## What Changes

- Add `scripts/install_global_skills.sh` that copies (default) or symlinks (`link` argument) the repo's `openspec-*` skills into the user-global skill root `${DSH_AGENTS_HOME:-$HOME/.agents}/skills`.
- Add `make install-skills` (and `make install-skills-link`) targets to run it.
- Run the installer on this machine so the skills are immediately available to every DSH session.
- Document global installation, refresh-after-`openspec update`, precedence (project skills override global ones) and the `~/.dsh/skills` alternative in the README.

No behavior change to the knowledge base, API or web app; this is developer-environment tooling and documentation only (`skip_specs: true`).

## Capabilities

### New Capabilities

_(none — tooling/documentation change with no spec-level behavior change.)_

### Modified Capabilities

_(none)_

## Impact

- **New file**: `scripts/install_global_skills.sh`; **Makefile** targets; **README** section.
- **Local environment**: `~/.agents/skills/openspec-*` created (outside the repository; not committed).
- **No dependency, API, UI or ontology changes.**
