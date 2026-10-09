#!/usr/bin/env python3
"""Offline health check for a git repository.

Usage: repo_health.py [path] [--json]

Checks docs, community files, CI, tests, dependency hygiene and committed
secrets, then prints a scored markdown report (or JSON with --json).
Standard library only; never touches the network.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

LARGE_FILE_BYTES = 5 * 1024 * 1024
SECRET_SCAN_MAX_BYTES = 1024 * 1024

SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Stripe live key": re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "OpenAI/Anthropic-style key": re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{32,}\b"),
    "Private key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
}

# manifest -> lockfiles that satisfy it
LOCKFILES = {
    "package.json": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock"],
    "pyproject.toml": ["poetry.lock", "uv.lock", "pdm.lock", "requirements.txt"],
    "Cargo.toml": ["Cargo.lock"],
    "go.mod": ["go.sum"],
    "Gemfile": ["Gemfile.lock"],
    "composer.json": ["composer.lock"],
}

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs)/"
    r"|(^|/)test_[^/]+\.py$|_test\.(py|go|rb|exs?)$"
    r"|\.(test|spec)\.[cm]?[jt]sx?$|Tests?\.(java|kt|cs|swift)$"
)


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def find_ci(repo, names):
    return (
        [n for n in names if n.startswith(".github/workflows/") and n.endswith((".yml", ".yaml"))]
        + [n for n in names if n in (".gitlab-ci.yml", ".travis.yml", "azure-pipelines.yml", "Jenkinsfile", ".circleci/config.yml")]
    )


def first_match(names, *candidates):
    lower = {n.lower(): n for n in names}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def check(repo):
    tracked = [n for n in git(repo, "ls-files", "-z").split("\0") if n]
    names = set(tracked)
    results = []

    def add(category, name, status, detail, weight):
        results.append({"category": category, "check": name, "status": status, "detail": detail, "weight": weight})

    # Docs
    readme = first_match(names, "README.md", "README.rst", "README.txt", "README", "readme.md")
    if not readme:
        add("Docs", "README", "fail", "No README at the repo root.", 3)
    else:
        text = (repo / readme).read_text(errors="replace")
        words = len(text.split())
        missing = [s for s, pat in (("install", r"install|setup|getting started|安装"), ("usage", r"usage|example|how to|使用|用法"))
                   if not re.search(pat, text, re.I)]
        if words < 50:
            add("Docs", "README", "warn", f"{readme} is only {words} words.", 3)
        elif missing:
            add("Docs", "README", "warn", f"{readme} has no section about: {', '.join(missing)}.", 3)
        else:
            add("Docs", "README", "pass", f"{readme}, {words} words, covers install and usage.", 3)

    lic = first_match(names, "LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "LICENCE")
    add("Docs", "License", "pass" if lic else "fail",
        lic or "No LICENSE file: others legally cannot reuse the code.", 3)

    # Community
    for label, cands, weight in (
        ("Contributing guide", ("CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"), 1),
        ("Code of conduct", ("CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"), 1),
        ("Security policy", ("SECURITY.md", ".github/SECURITY.md"), 1),
    ):
        found = first_match(names, *cands)
        add("Community", label, "pass" if found else "warn", found or "Missing.", weight)

    issue_tpl = [n for n in names if n.startswith(".github/ISSUE_TEMPLATE/")]
    add("Community", "Issue templates", "pass" if issue_tpl else "warn",
        f"{len(issue_tpl)} template file(s)." if issue_tpl else "No .github/ISSUE_TEMPLATE/.", 1)
    pr_tpl = first_match(names, ".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md",
                         "PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md")
    add("Community", "PR template", "pass" if pr_tpl else "warn", pr_tpl or "Missing.", 1)

    # Engineering
    ci = find_ci(repo, names)
    add("Engineering", "CI", "pass" if ci else "fail",
        ", ".join(sorted(ci)[:5]) if ci else "No CI config found (GitHub Actions, GitLab CI, ...).", 2)

    tests = [n for n in tracked if TEST_PATH.search(n)]
    add("Engineering", "Tests", "pass" if tests else "fail",
        f"{len(tests)} test file(s)." if tests else "No test files found.", 2)

    add("Engineering", ".gitignore", "pass" if ".gitignore" in names else "warn",
        "Present." if ".gitignore" in names else "Missing.", 1)

    for manifest, locks in LOCKFILES.items():
        dirs = {str(Path(n).parent) for n in tracked if Path(n).name == manifest}
        for d in sorted(dirs):
            prefix = "" if d == "." else d + "/"
            if not any(prefix + l in names for l in locks):
                add("Engineering", "Lockfile", "warn", f"{prefix}{manifest} has no lockfile committed.", 1)

    # Security
    env_files = [n for n in tracked if re.search(r"(^|/)(\.env(\.[^/]*)?|[^/]+\.env)$", n) and not n.endswith((".example", ".sample", ".template"))]
    add("Security", "Committed .env files", "fail" if env_files else "pass",
        ", ".join(env_files) if env_files else "None tracked.", 3)

    hits = []
    for n in tracked:
        p = repo / n
        try:
            if not p.is_file() or p.stat().st_size > SECRET_SCAN_MAX_BYTES:
                continue
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for label, pat in SECRET_PATTERNS.items():
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{label} in {n}:{line}")
    add("Security", "Secrets in tracked files", "fail" if hits else "pass",
        "; ".join(hits[:10]) + (f" (+{len(hits) - 10} more)" if len(hits) > 10 else "") if hits else "No known key patterns found.", 3)

    big = []
    for n in tracked:
        p = repo / n
        if p.is_file() and p.stat().st_size > LARGE_FILE_BYTES:
            big.append(f"{n} ({p.stat().st_size // (1024 * 1024)} MB)")
    add("Engineering", "Large files", "warn" if big else "pass",
        ", ".join(big[:5]) + " (consider Git LFS)" if big else "No tracked file over 5 MB.", 1)

    # Activity
    last = git(repo, "log", "-1", "--format=%ct").strip()
    if last:
        days = int((time.time() - int(last)) / 86400)
        status = "pass" if days <= 90 else "warn" if days <= 365 else "fail"
        add("Activity", "Last commit", status, f"{days} day(s) ago.", 1)
    else:
        add("Activity", "Last commit", "fail", "No commits.", 1)

    return results


def score(results):
    points = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
    total = sum(r["weight"] for r in results)
    got = sum(r["weight"] * points[r["status"]] for r in results)
    return round(100 * got / total) if total else 0


def render(repo, results):
    icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
    s = score(results)
    grade = "A" if s >= 90 else "B" if s >= 75 else "C" if s >= 60 else "D" if s >= 40 else "F"
    lines = [f"# Repo health: {repo.name}", "", f"**Score: {s}/100 ({grade})**", ""]
    for cat in dict.fromkeys(r["category"] for r in results):
        lines += [f"## {cat}", ""]
        lines += [f"- {icon[r['status']]} **{r['check']}**: {r['detail']}" for r in results if r["category"] == cat]
        lines.append("")
    fixes = sorted((r for r in results if r["status"] != "pass"), key=lambda r: (r["status"] != "fail", r["category"] != "Security", -r["weight"]))
    if fixes:
        lines += ["## Fix first", ""]
        lines += [f"{i}. {r['check']}: {r['detail']}" for i, r in enumerate(fixes[:5], 1)]
    return "\n".join(lines)


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    path = Path(args[0] if args else ".").resolve()
    top = git(path, "rev-parse", "--show-toplevel").strip()
    if not top:
        err = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stderr.strip()
        print(f"error: {path} is not a usable git repository: {err}", file=sys.stderr)
        return 1
    repo = Path(top)
    results = check(repo)
    if as_json:
        print(json.dumps({"repo": str(repo), "score": score(results), "checks": results}, ensure_ascii=False, indent=2))
    else:
        print(render(repo, results))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
