"""Smoke tests for the skill scripts. Run: python3 -m unittest discover tests"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

# Built at runtime so this file does not itself trip the secret scanner.
FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"

ROOT = Path(__file__).resolve().parent.parent
HEALTH = ROOT / "skills/repo-health/scripts/repo_health.py"
INSTALL = ROOT / "install.sh"
RELEASE = ROOT / "skills/release-notes/scripts/collect_release.py"
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
        repo = make_repo({"README.md": "# x\n", ".env": f"AWS={FAKE_AWS_KEY}\n"})
        report, checks = self.health(repo)
        self.assertEqual(checks["Secrets in tracked files"]["status"], "fail")
        self.assertIn(".env:1", checks["Secrets in tracked files"]["detail"])
        self.assertNotIn(FAKE_AWS_KEY, json.dumps(report))
        self.assertEqual(checks["Committed .env files"]["status"], "fail")

    def test_named_env_files_count_but_examples_do_not(self):
        repo = make_repo({"config/dev.env": "A=1\n", ".env.example": "A=\n"})
        _, checks = self.health(repo)
        self.assertEqual(checks["Committed .env files"]["detail"], "config/dev.env")

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


class ReleaseNotesTest(unittest.TestCase):
    def commit(self, repo, msg, body=None):
        with open(repo / "f", "a") as f:
            f.write(msg + "\n")
        run(["git", "add", "-A"], repo)
        run(["git", "commit", "-qm", msg] + (["-m", body] if body else []), repo)

    def release(self, repo):
        return run(["python3", str(RELEASE), "--no-github"], repo)

    def test_range_starts_at_last_tag_and_suggests_minor_for_feature(self):
        repo = make_repo({"a.txt": "a\n"})
        run(["git", "tag", "v1.2.3"], repo)
        self.commit(repo, "fix: handle empty input (#5)")
        self.commit(repo, "feat: add export")
        out = self.release(repo)
        self.assertIn("Suggested next version: v1.3.0", out)
        self.assertIn("Commits: 2   PRs referenced: 1", out)
        self.assertNotIn("init", out.split("## Commits")[1])

    def test_breaking_change_bumps_major(self):
        repo = make_repo({"a.txt": "a\n"})
        run(["git", "tag", "v1.2.3"], repo)
        self.commit(repo, "refactor: new config format", "BREAKING CHANGE: config.yml renamed")
        self.assertIn("Suggested next version: v2.0.0", self.release(repo))

    def test_patch_when_only_fixes(self):
        repo = make_repo({"a.txt": "a\n"})
        run(["git", "tag", "0.4.1"], repo)
        self.commit(repo, "Fix crash on save")
        self.assertIn("Suggested next version: 0.4.2", self.release(repo))


class InstallTest(unittest.TestCase):
    def install(self, *args):
        home = Path(tempfile.mkdtemp())
        env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
        subprocess.run(["bash", str(INSTALL), *args], env=env, capture_output=True, text=True, check=True)
        return home

    def skills_in(self, path):
        return sorted(p.parent.name for p in path.glob("*/SKILL.md"))

    def test_codex_installs_into_agents_skills(self):
        home = self.install("codex")
        self.assertEqual(self.skills_in(home / ".agents/skills"), ["issue-triage", "pr-description", "release-notes", "repo-health"])
        self.assertTrue((home / ".agents/skills/repo-health/agents/openai.yaml").is_file())
        self.assertFalse((home / ".claude").exists())

    def test_all_installs_for_both_tools(self):
        home = self.install("all")
        self.assertEqual(len(self.skills_in(home / ".claude/skills")), 4)
        self.assertEqual(len(self.skills_in(home / ".agents/skills")), 4)

    def test_project_install(self):
        project = Path(tempfile.mkdtemp())
        self.install("claude", "--project", str(project))
        self.assertEqual(len(self.skills_in(project / ".claude/skills")), 4)


class SkillFormatTest(unittest.TestCase):
    def test_every_skill_has_frontmatter_and_codex_metadata(self):
        for skill in (ROOT / "skills").iterdir():
            text = (skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill.name)
            front = text.split("---")[1]
            self.assertIn(f"name: {skill.name}\n", front)
            self.assertIn("description: ", front)
            self.assertIn("display_name:", (skill / "agents/openai.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
