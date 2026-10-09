"""Smoke tests for the skill scripts. Run: python3 -m unittest discover tests"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEALTH = ROOT / "skills/repo-health/scripts/repo_health.py"
COLLECT = ROOT / "skills/pr-description/scripts/collect_changes.sh"


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout


def make_repo(files):
    tmp = Path(tempfile.mkdtemp())
    run(["git", "init", "-q", "-b", "main"], tmp)
    run(["git", "config", "user.email", "test@example.com"], tmp)
    run(["git", "config", "user.name", "test"], tmp)
    for name, content in files.items():
        path = tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    run(["git", "add", "-A"], tmp)
    run(["git", "commit", "-qm", "init"], tmp)
    return tmp


class RepoHealthTest(unittest.TestCase):
    def health(self, repo):
        report = json.loads(run(["python3", str(HEALTH), str(repo), "--json"], repo))
        return report, {c["check"]: c for c in report["checks"]}

    def test_flags_committed_secret_and_env(self):
        repo = make_repo({"README.md": "# x\n", ".env": "AWS=AKIAABCDEFGHIJKLMNOP\n"})
        report, checks = self.health(repo)
        self.assertEqual(checks["Secrets in tracked files"]["status"], "fail")
        self.assertIn(".env:1", checks["Secrets in tracked files"]["detail"])
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", json.dumps(report))
        self.assertEqual(checks["Committed .env files"]["status"], "fail")

    def test_well_kept_repo_scores_high(self):
        readme = "# x\n\n" + "A useful tool. " * 30 + "\n\n## Install\n\npip install x\n\n## Usage\n\nx run\n"
        repo = make_repo({
            "README.md": readme, "LICENSE": "MIT", ".gitignore": "*.pyc\n",
            "CONTRIBUTING.md": "c", "CODE_OF_CONDUCT.md": "c", "SECURITY.md": "s",
            ".github/ISSUE_TEMPLATE/bug.md": "b", ".github/pull_request_template.md": "p",
            ".github/workflows/ci.yml": "on: push", "tests/test_x.py": "def test(): pass\n",
        })
        report, _ = self.health(repo)
        self.assertGreaterEqual(report["score"], 95)


class CollectChangesTest(unittest.TestCase):
    def test_lists_commits_and_files_against_base(self):
        repo = make_repo({"a.txt": "one\n"})
        run(["git", "checkout", "-qb", "feature"], repo)
        (repo / "b.txt").write_text("two\n")
        run(["git", "add", "-A"], repo)
        run(["git", "commit", "-qm", "Add b"], repo)
        out = run(["bash", str(COLLECT), "main"], repo)
        self.assertIn("- Add b", out)
        self.assertIn("### b.txt", out)
        self.assertNotIn("### a.txt", out)


if __name__ == "__main__":
    unittest.main()
