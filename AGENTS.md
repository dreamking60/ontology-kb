# AGENTS.md — Operating Procedure for AI Agents in This Repository

This repository is developed **spec-first with OpenSpec** (spec-driven development).
Before writing code, plan with OpenSpec; get the plan reviewed; only then implement.

## OpenSpec layout

- `openspec/changes/<change-name>/` — one folder per in-flight change:
  `proposal.md`, `specs/<capability-path>/spec.md` (delta spec), `design.md`, `tasks.md`
- `openspec/changes/archive/<date>-<change-name>/` — archived, completed changes
- `openspec/specs/` — main specs (source of truth), updated only by archive/sync
- `openspec/config.yaml` — project context and language (English; keep SHALL/MUST
  and structural headings in English)

## Workflow (the canonical loop)

1. **Explore** (optional) — think through an idea before committing: skill
   `openspec-explore` / CLI `openspec explore`.
2. **Propose** — create the change with all planning artifacts in one step:
   skill `openspec-propose` / CLI `openspec propose "<name>"`. This creates
   `openspec/changes/<name>/` with proposal, delta specs, design, and tasks.
   **Planning only — never edit project code during propose.**
3. **Review** — present the artifacts to the user and wait for approval before
   implementation starts.
4. **Apply** — implement the tasks from `tasks.md` one by one:
   skill `openspec-apply-change` / CLI `openspec apply --change "<name>"`.
5. **Update** (when needed) — revise planning artifacts if the plan changes:
   skill `openspec-update-change` / CLI `openspec update --change "<name>"`.
6. **Sync** (when needed) — fold delta specs into main specs without archiving:
   skill `openspec-sync-specs` / CLI `openspec sync --change "<name>"`.
7. **Archive** — after implementation is verified and complete:
   skill `openspec-archive-change` / CLI `openspec archive --change "<name>"`.
   This moves the change to the archive and updates main specs.

## Rules for agents

- **Never write code before an OpenSpec change exists and the user has approved
  its plan.** If the user asks to build something and no change folder exists,
  start with `openspec-propose`.
- **Never archive or sync a change without the user's confirmation.**
- Planning artifacts are created/edited with `openspec` commands (the skills use
  `Bash(openspec:*)`); keep artifacts coherent with each other and with specs.
- Preserve existing capability paths under `specs/`; follow project organization
  for new capabilities.
- Requirements prose in artifacts is English by default (see `config.yaml`),
  with OpenSpec structural headings and SHALL/MUST keywords kept in English.

## Invocation

- Skills in `.agents/skills/openspec-*` (vendor-neutral `agents` tree): ask the
  agent to use the matching skill, e.g. `openspec-propose`, or the canonical
  user-facing spelling `/openspec-propose`.
- CLI is installed globally: `openspec` (Node 20.19+; requires `@fission-ai/openspec`).
  Run `openspec --help` for commands, `openspec validate` to validate all changes.

## Housekeeping

- `openspec update` refreshes agent skills/commands after a CLI upgrade.
- Keep `openspec/changes/archive/` history; don't hand-delete archived changes.
