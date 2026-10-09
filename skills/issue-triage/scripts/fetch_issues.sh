#!/usr/bin/env bash
# Print a repo's labels and open issues as compact markdown for triage.
# Usage: [ALL=1] fetch_issues.sh [owner/repo] [limit]
# Uses the REST API through `gh api`, so it only needs `gh auth login`.
set -euo pipefail

command -v gh >/dev/null || { echo "error: GitHub CLI (gh) is not installed" >&2; exit 1; }

repo="${1:-}"
if [[ -z "$repo" ]]; then
  url="$(git remote get-url origin 2>/dev/null || true)"
  repo="$(sed -E 's#^(git@[^:]+:|https?://[^/]+/)##; s#\.git$##' <<<"$url")"
fi
[[ "$repo" == */* ]] || { echo "error: pass owner/repo, or run inside a clone with an origin remote" >&2; exit 1; }
limit="${2:-50}"

echo "# Repo: $repo"
echo
echo "## Existing labels"
gh api --paginate "repos/$repo/labels?per_page=100" \
  --jq '.[] | "- \(.name)" + (if (.description // "") != "" then ": \(.description)" else "" end)'

echo
if [[ "${ALL:-0}" == "1" ]]; then echo "## Open issues"; else echo "## Open issues without labels"; fi

# The issues endpoint also returns PRs; drop them. Fetch extra pages so the limit still fills after filtering.
gh api --paginate "repos/$repo/issues?state=open&per_page=100&sort=created&direction=desc" \
  --jq ".[] | select(.pull_request | not) | select(env.ALL == \"1\" or (.labels | length) == 0) |
      \"\n### #\(.number) \(.title)\",
      \"author: \(.user.login) | opened: \(.created_at[:10]) | comments: \(.comments) | labels: \([.labels[].name] | join(\", \") | if . == \"\" then \"none\" else . end)\",
      \"\",
      ((.body // \"\") | if length > 1500 then .[:1500] + \"\n... [truncated]\" else . end),
      \"<<END>>\"" \
  | awk -v max="$limit" '/^<<END>>$/ { if (++n >= max) exit; next } { print }' \
  || [[ $? -eq 141 ]]  # gh gets SIGPIPE when awk stops early at the limit
