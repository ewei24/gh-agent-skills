#!/usr/bin/env python3
"""Collect everything needed to write release notes for a range of commits.

Usage: collect_release.py [--from REF] [--to REF] [--repo OWNER/REPO] [--no-github]

--from defaults to the latest tag reachable from --to (or the first commit if
there are no tags); --to defaults to HEAD. When the GitHub CLI is available,
PR titles, labels and authors are looked up for every PR number found in the
commit messages; pass --no-github to skip that.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys

CONVENTIONAL = re.compile(r"^(?P<type>[a-z]+)(\([^)]*\))?(?P<bang>!)?:\s")
PR_REF = re.compile(r"Merge pull request #(\d+)|\(#(\d+)\)\s*$")
SEMVER = re.compile(r"^(?P<prefix>v?)(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")


def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"error: git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def default_from(to):
    tag = git("describe", "--tags", "--abbrev=0", to, check=False)
    if tag:
        return tag, tag
    root = git("rev-list", "--max-parents=0", to).splitlines()[-1]
    return root, None


def commits(rng):
    sep, end = "\x1f", "\x1e"
    out = git("log", "--no-merges", f"--format=%H{sep}%an{sep}%s{sep}%b{end}", rng)
    merges = git("log", "--merges", f"--format=%s{sep}%b{end}", rng)
    items = []
    for raw in filter(None, (r.strip() for r in out.split(end))):
        sha, author, subject, body = (raw.split(sep) + [""] * 4)[:4]
        items.append({"sha": sha[:7], "author": author, "subject": subject, "body": body.strip()})
    pr_numbers = set()
    for text in [c["subject"] for c in items] + [m.split(sep)[0] for m in merges.split(end) if m.strip()]:
        m = PR_REF.search(text.strip())
        if m:
            pr_numbers.add(int(m.group(1) or m.group(2)))
    return items, sorted(pr_numbers)


def repo_slug(explicit):
    if explicit:
        return explicit
    url = git("remote", "get-url", "origin", check=False)
    m = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    return m.group(1) if m else None


def fetch_prs(repo, numbers):
    prs = []
    for n in numbers:
        result = subprocess.run(["gh", "api", f"repos/{repo}/pulls/{n}"], capture_output=True, text=True)
        if result.returncode != 0:
            prs.append({"number": n, "error": "could not fetch"})
            continue
        pr = json.loads(result.stdout)
        prs.append({
            "number": n,
            "title": pr["title"],
            "author": pr["user"]["login"],
            "labels": [l["name"] for l in pr["labels"]],
            "body": (pr.get("body") or "")[:800],
        })
    return prs


def suggest_version(last_tag, items):
    kinds = set()
    for c in items:
        m = CONVENTIONAL.match(c["subject"])
        if (m and m.group("bang")) or "BREAKING CHANGE" in c["body"]:
            kinds.add("breaking")
        elif m and m.group("type") == "feat":
            kinds.add("feature")
    m = SEMVER.match(last_tag or "")
    if not m:
        return None, sorted(kinds)
    major, minor, patch = int(m["major"]), int(m["minor"]), int(m["patch"])
    if "breaking" in kinds and major > 0:
        major, minor, patch = major + 1, 0, 0
    elif "breaking" in kinds or "feature" in kinds:
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{m['prefix']}{major}.{minor}.{patch}", sorted(kinds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_ref")
    ap.add_argument("--to", default="HEAD")
    ap.add_argument("--repo")
    ap.add_argument("--no-github", action="store_true")
    args = ap.parse_args()

    git("rev-parse", "--is-inside-work-tree")
    if args.from_ref:
        start, last_tag = args.from_ref, args.from_ref
        rng = f"{start}..{args.to}"
    else:
        start, last_tag = default_from(args.to)
        # with no tags, include the root commit itself
        rng = f"{start}..{args.to}" if last_tag else args.to

    items, pr_numbers = commits(rng)
    repo = repo_slug(args.repo)
    prs = []
    if pr_numbers and repo and not args.no_github and shutil.which("gh"):
        prs = fetch_prs(repo, pr_numbers)
    next_version, signals = suggest_version(last_tag, items)

    print(f"# Release range: {last_tag or '(first commit)'} .. {args.to}")
    print(f"Repo: {repo or 'unknown'}")
    print(f"Last tag: {last_tag or 'none'}")
    print(f"Suggested next version: {next_version or 'n/a (no semver tag found)'}"
          + (f"  [signals: {', '.join(signals)}]" if signals else ""))
    print(f"Commits: {len(items)}   PRs referenced: {len(pr_numbers)}")
    print("\n## Diffstat")
    print(git("diff", "--shortstat", rng.split("..")[0], args.to) if ".." in rng else "(whole history)")
    print("\n## Contributors")
    for name in sorted({c["author"] for c in items} | {p["author"] for p in prs if "author" in p}):
        print(f"- {name}")
    if prs:
        print("\n## Pull requests")
        for p in prs:
            if "error" in p:
                print(f"\n### #{p['number']} (could not fetch details)")
                continue
            labels = ", ".join(p["labels"]) or "none"
            print(f"\n### #{p['number']} {p['title']}\nauthor: @{p['author']} | labels: {labels}")
            if p["body"]:
                print(p["body"])
    print("\n## Commits")
    for c in items:
        print(f"- {c['sha']} {c['subject']} ({c['author']})")
        if c["body"]:
            for line in c["body"].splitlines()[:6]:
                print(f"    {line}")


if __name__ == "__main__":
    main()
