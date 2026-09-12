#!/usr/bin/env bash
# Install / refresh the OpenSpec agent skills into the user-global skill root so
# every DeepSeek Harness session — any workspace, any standard mode — can load
# them (DSH discovers <agentsHome>/skills, default ~/.agents/skills).
#
# Usage:
#   bash scripts/install_global_skills.sh          # copy (default, robust)
#   bash scripts/install_global_skills.sh link     # symlink (auto-fresh after
#                                                  # `openspec update` in this repo)
#
# Re-run after upgrading OpenSpec and running `openspec update` in this project.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/.agents/skills"
DEST="${DSH_AGENTS_HOME:-$HOME/.agents}/skills"
MODE="${1:-copy}"

if [ ! -d "$SRC" ]; then
  echo "ERROR: $SRC not found — run 'openspec update' (or 'openspec init --tools agents') first." >&2
  exit 1
fi
case "$MODE" in copy|link) ;; *) echo "ERROR: mode must be 'copy' or 'link' (got '$MODE')." >&2; exit 1 ;; esac

mkdir -p "$DEST"
shopt -s nullglob
installed=0
for skill in "$SRC"/openspec-*; do
  [ -d "$skill" ] || continue
  name="$(basename "$skill")"
  rm -rf "$DEST/$name"
  if [ "$MODE" = "link" ]; then
    ln -s "$skill" "$DEST/$name"
  else
    cp -R "$skill" "$DEST/$name"
  fi
  echo "  ✓ $name → $DEST/$name"
  installed=$((installed + 1))
done
if [ "$installed" -eq 0 ]; then
  echo "ERROR: no openspec-* skills found under $SRC." >&2
  exit 1
fi
# Keep the vendor-neutral target marker alongside the skills (informational).
if [ -f "$SRC/.openspec-target" ] && [ ! -e "$DEST/.openspec-target" ]; then
  cp "$SRC/.openspec-target" "$DEST/.openspec-target"
fi
echo "Installed $installed OpenSpec skill(s) [$MODE] into $DEST"
echo "They are now available to every DSH session; refresh with 'make install-skills' after 'openspec update'."
