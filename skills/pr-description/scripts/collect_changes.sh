#!/usr/bin/env bash
# Print commits, diffstat and a size-capped diff between a base branch and HEAD.
# Usage: collect_changes.sh [base-branch] [max-lines-per-file]
set -euo pipefail

max_lines="${2:-200}"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "error: not inside a git repository" >&2; exit 1; }

base="${1:-}"
if [[ -z "$base" ]]; then
  base="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [[ -z "$base" ]]; then
    for candidate in origin/main origin/master main master; do
      if git rev-parse --verify --quiet "$candidate" >/dev/null; then base="$candidate"; break; fi
    done
  fi
fi
[[ -n "$base" ]] || { echo "error: could not find a base branch; pass one explicitly" >&2; exit 1; }

merge_base="$(git merge-base "$base" HEAD)"

echo "# Base: $base ($(git rev-parse --short "$merge_base"))"
echo "# Head: $(git rev-parse --abbrev-ref HEAD) ($(git rev-parse --short HEAD))"
echo
echo "## Commits"
git log --no-merges --format='- %s%n%w(0,2,2)%b' "$merge_base"..HEAD | sed '/^  $/d'
echo
echo "## Diffstat"
git diff --stat "$merge_base"
echo
if ! git diff --quiet HEAD; then
  echo "## Note: there are uncommitted changes; they are included in the diff below."
  echo
fi
echo "## Diff (each file capped at $max_lines lines)"
git diff --name-only "$merge_base" | while IFS= read -r file; do
  echo
  echo "### $file"
  git diff "$merge_base" -- "$file" | awk -v max="$max_lines" '
    NR <= max { print }
    END { if (NR > max) printf "... [%d more lines truncated]\n", NR - max }'
done
