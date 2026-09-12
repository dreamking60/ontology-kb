## 1. Installer script

- [x] 1.1 Add `scripts/install_global_skills.sh` (idempotent copy of `.agents/skills/openspec-*` into `${DSH_AGENTS_HOME:-$HOME/.agents}/skills`, `link` argument for symlinks, prints each installed skill); verify running it twice succeeds and lists the 6 skills
- [x] 1.2 Add `make install-skills` and `make install-skills-link` targets; verify `make install-skills` runs the script

## 2. Global installation on this machine

- [x] 2.1 Run `make install-skills`; verify `~/.agents/skills/openspec-*` contains the 6 skill directories each with `SKILL.md`
- [x] 2.2 Verify the discovery roots DSH reads are as documented (skill-filesystem source: project `.dsh/skills`/`.agents/skills`, user `$DSH_HOME/skills`, `$DSH_AGENTS_HOME|~/.agents/skills`) and that the installed path matches the `user-agents` root

## 3. Documentation and acceptance

- [x] 3.1 Document in README: global install command, refresh after `openspec update`, project-over-global precedence, `~/.dsh/skills` alternative; verify README renders and commands are accurate
- [x] 3.2 Commit + push; verify `git status` clean, remote in sync, and the repo contains no machine-specific paths (global install stays outside the repository)
