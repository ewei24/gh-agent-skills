#!/usr/bin/env bash
# Install the skills for Claude Code, OpenAI Codex, or both.
#
# Usage: ./install.sh [claude|codex|all] [--project DIR]
#
#   claude    copy to ~/.claude/skills   (or DIR/.claude/skills with --project)
#   codex     copy to ~/.agents/skills   (or DIR/.agents/skills with --project)
#   all       both
#
# With no target, installs for every tool it finds on this machine.
set -euo pipefail

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"
target=""
project=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    claude|codex|all) target="$1" ;;
    --project) project="${2:?--project needs a directory}"; shift ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 1 ;;
  esac
  shift
done

if [[ -z "$target" ]]; then
  found=()
  { command -v claude >/dev/null || [[ -d "$HOME/.claude" ]]; } && found+=(claude)
  { command -v codex >/dev/null || [[ -d "$HOME/.codex" || -d "$HOME/.agents" ]]; } && found+=(codex)
  case "${#found[@]}" in
    0) echo "Neither Claude Code nor Codex found; installing for both." >&2; target=all ;;
    2) target=all ;;
    *) target="${found[0]}" ;;
  esac
fi

base="${project:-$HOME}"
dests=()
[[ "$target" == claude || "$target" == all ]] && dests+=("$base/.claude/skills")
[[ "$target" == codex || "$target" == all ]] && dests+=("$base/.agents/skills")

for dest in "${dests[@]}"; do
  mkdir -p "$dest"
  for skill in "$src"/*/; do
    name="$(basename "$skill")"
    rm -rf "${dest:?}/${name:?}"
    cp -R "$skill" "$dest/$name"
  done
  echo "Installed $(ls -d "$src"/*/ | wc -l | tr -d ' ') skills into $dest"
done

[[ "$target" == claude || "$target" == all ]] && echo "Claude Code: just ask, e.g. \"run a health check on this repo\"."
[[ "$target" == codex || "$target" == all ]] && echo "Codex: just ask, or type \$ to pick a skill (restart Codex if it does not show up)."
exit 0
