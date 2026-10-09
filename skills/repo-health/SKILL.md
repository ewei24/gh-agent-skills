---
name: repo-health
description: Run a health check on a git repository (docs, license, CI, tests, community files, committed secrets, large files, activity) and give a scored report with the top fixes. Use when the user asks to audit, check up on, review the health of, or prepare a repo for open-sourcing.
---

# Repo health

Score a repository out of 100 and tell the user the few fixes that matter most.

## Steps

1. Run the checker from anywhere inside the repo (Python 3, no dependencies, no network):

   ```bash
   python3 scripts/repo_health.py [path-to-repo]
   python3 scripts/repo_health.py [path-to-repo] --json   # machine-readable
   ```

2. Read the report. It covers:
   - **Docs**: README length and install/usage sections, LICENSE
   - **Community**: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue and PR templates
   - **Engineering**: CI config, test files, `.gitignore`, lockfiles, files over 5 MB
   - **Security**: tracked `.env` files and common API key / private key patterns
   - **Activity**: days since the last commit

3. Check the findings before reporting them. The script uses simple patterns:
   - A secret "hit" may be a test fixture or a documented fake key. Open the line and confirm.
   - "No tests" may be wrong for unusual layouts. Glance at the tree.
   - Missing community files matter for public projects, much less for personal ones.

4. Reply with the score, then the top 3 to 5 fixes in priority order, each with one line on why it matters. Real secrets come first, always.

5. Offer to make the fixes. Generate files the repo is missing (LICENSE, CONTRIBUTING.md, a basic CI workflow, issue/PR templates) only when the user says yes, and match the repo's language and tooling.

## Rules

- If a real secret is committed, tell the user to **rotate it first**. Deleting the file does not remove it from git history.
- Do not pick a license for the user. Ask which one (MIT, Apache-2.0, GPL-3.0 ...) and explain the difference in one line each if they are unsure.
- Never print a full secret value in the report; the script prints only file and line.
