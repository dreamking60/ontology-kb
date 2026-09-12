## Context

DSH's `dsh-skill-filesystem` resolves skill roots in this order (verified in the installed package source): project roots `<projectRoot>/.dsh/skills` and `<projectRoot>/.agents/skills` (higher rank), then custom dirs, then user roots `<dshHome>/skills` (`~/.dsh`, overridable via `$DSH_HOME`) and `<agentsHome>/skills` (`~/.agents`, overridable via `$DSH_AGENTS_HOME`), then bundled skills. OpenSpec's `agents` tool target writes project-local skills only, so other workspaces currently see no OpenSpec skills.

## Goals / Non-Goals

**Goals:** OpenSpec skills present for every DSH session in any workspace/mode; one command to install and one to refresh after `openspec update`; project-local skills keep precedence.

**Non-Goals:** changing OpenSpec's own generator; committing generated skills into every project; per-mode configuration inside DSH.

## Decisions

### D1: Install into `${DSH_AGENTS_HOME:-$HOME/.agents}/skills`

The `.agents` root is the vendor-neutral shared skills root (also read by Codex/Zed and by DSH's `user-agents` rank), so one installation serves the widest set of sessions; `~/.dsh/skills` is left as an alternative for users who prefer DSH-only scoping.

### D2: Copy by default, symlink optional

`scripts/install_global_skills.sh` copies `openspec-*` skill directories (idempotent: removes the destination skill dir first). A `link` argument symlinks instead so `openspec update` in this repo automatically refreshes the global view — at the cost of depending on this checkout's presence. Copy is the default because global availability should not break if the repo moves.

### D3: Refresh is explicit, project overrides global

After upgrading OpenSpec (`openspec update` regenerates project skills), run `make install-skills` again to refresh the global copies. Because project roots rank above user roots, a project's own generated skills always win over the global copy with the same name — no behavioural surprises in OpenSpec-managed repos.

## Risks / Trade-offs

- [Global copies drift from upstream OpenSpec versions] → `make install-skills` refresh documented; symlink mode available for automatic freshness.
- [Duplicate skill names between project and global roots] → DSH ranks project roots higher, so the project copy wins; identical content in practice.
- [Machine-specific installation is not captured in git] → the installer script + make target are committed, so any machine can reproduce it in one command.

## Migration Plan

Run `make install-skills` (already executed on this machine). Rollback: delete the `openspec-*` directories from the global root; the repo is unaffected.

## Open Questions

- Whether OpenSpec later grows a first-class `--global` target (then this script becomes unnecessary and can be retired).
