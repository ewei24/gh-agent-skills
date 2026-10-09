---
name: pr-description
description: Write a pull request title and description from the current branch's commits and diff. Use when the user asks to write, draft, or improve a PR description, or is about to open a PR.
---

# PR description

Write a PR title and body a reviewer can read in under a minute, grounded only in what the diff actually changes.

## Steps

1. Collect the change set:

   ```bash
   bash scripts/collect_changes.sh [base-branch]
   ```

   The script prints the base branch it used, the commit list, a diffstat, and the diff (truncated per file so it fits in context). If no base is given it uses the remote's default branch, falling back to `main`.

2. Look for a PR template in the repo (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/PULL_REQUEST_TEMPLATE/*.md`, `PULL_REQUEST_TEMPLATE.md`, `docs/PULL_REQUEST_TEMPLATE.md`). If one exists, fill in its sections instead of the format below. Skip template sections that ask for secrets or anything unrelated to the diff.

3. Read the diff, not just the commit messages. Commit messages can be stale or vague; the diff is the truth.

4. Write the title: imperative mood, under 70 characters, says what changes for the user or the codebase (`Add retry to webhook sender`, not `Update sender.ts`). Follow the repo's convention if recent commits use one (e.g. `feat:` prefixes).

5. Write the body in this shape when there is no template:

   ```markdown
   ## Before
   One short paragraph: what a user or developer saw before this change.

   ## After
   One short paragraph: what they see now.

   ## How
   2-5 bullets on the approach, naming the key files or functions.

   ## Testing
   What was run or how to verify. If nothing was tested, say so plainly.
   ```

   Add a `## Notes for reviewers` section only when there is something risky, a migration, a breaking change, or a spot that deserves a careful look.

6. Show the title and body to the user. Only if they ask, apply it:

   ```bash
   gh pr create --title "<title>" --body-file <file>      # new PR
   gh pr edit <number> --title "<title>" --body-file <file>  # existing PR
   ```

## Rules

- Never invent tests, benchmarks, issue numbers, or screenshots that are not in the diff or conversation.
- Mention breaking changes, new dependencies, config/env changes, and DB migrations explicitly; reviewers miss these most.
- Link issues only when a commit message or branch name references them (`fixes #123`).
- Keep it short. A 20-line diff gets a 5-line description.
