# gh-agent-skills

Agent skills for everyday GitHub chores. Works with **Claude Code** and **OpenAI Codex** (CLI, IDE extension and the ChatGPT app), or any agent that reads `SKILL.md` skills. Install once, then ask in plain language:

| Skill | Ask it | What it does |
|---|---|---|
| [`pr-description`](skills/pr-description/SKILL.md) | "write the PR description" | Reads your branch's commits and diff, writes a title and a Before / After / How / Testing body, follows the repo's PR template if it has one. |
| [`issue-triage`](skills/issue-triage/SKILL.md) | "triage the open issues" | Proposes type, priority, duplicates and needs-info for unlabeled issues using the repo's own labels, then applies only what you approve. |
| [`repo-health`](skills/repo-health/SKILL.md) | "give this repo a health check" | Scores the repo out of 100 (docs, license, CI, tests, community files, committed secrets, large files, activity) and lists the fixes that matter most. |
| [`release-notes`](skills/release-notes/SKILL.md) | "write release notes" | Groups the commits and PRs since the last tag into breaking changes, features, fixes and docs, written for users, and suggests the next version number. Publishes only when you say so. |

## Install

```bash
git clone https://github.com/ewei24/gh-agent-skills
cd gh-agent-skills
./install.sh            # installs for whichever of Claude Code / Codex you have
```

Or pick explicitly:

| Command | Installs into | Used by |
|---|---|---|
| `./install.sh claude` | `~/.claude/skills/` | Claude Code |
| `./install.sh codex` | `~/.agents/skills/` | OpenAI Codex (CLI, IDE extension, ChatGPT app) |
| `./install.sh all` | both | both |
| `./install.sh codex --project path/to/repo` | `path/to/repo/.agents/skills/` | one project only (same for `claude`) |

Re-run it after `git pull` to update.

**Codex notes:** in Codex you can also type `$` (CLI / IDE) or `@` (ChatGPT app) to pick a skill by name. If a new skill doesn't show up, restart Codex. Each skill ships an `agents/openai.yaml` with its display name and a starter prompt for the ChatGPT app.

## Requirements

- `git` and `bash` for all skills
- Python 3.8+ for `repo-health` and `release-notes` (standard library only)
- [GitHub CLI](https://cli.github.com/) (`gh auth login`) for `issue-triage`, and for `pr-description` if you want it to create or edit the PR for you

## Usage

In Claude Code or Codex, just ask: "write the PR description for this branch", "triage the open issues", "run a health check on this repo", or "write release notes since the last tag". The agent picks the matching skill.

The health check also runs on its own, without an agent:

```bash
python3 skills/repo-health/scripts/repo_health.py path/to/repo
```

```
# Repo health: my-app

**Score: 60/100 (C)**
...
## Fix first

1. Secrets in tracked files: AWS access key in config/dev.env:3
2. License: No LICENSE file: others legally cannot reuse the code.
3. Tests: No test files found.
```

## Safety

- The skills never comment on, close, or relabel issues, edit PRs, or publish releases without your go-ahead.
- Issue and PR text from other people is treated as data, not instructions.
- `repo-health` reports where a secret is (file and line), never the secret itself.

## 中文说明

一组处理 GitHub 日常杂活的 agent 技能，支持 **Claude Code** 和 **OpenAI Codex**（命令行、IDE 插件和 ChatGPT 桌面版）。装好后直接用自然语言调用：

- **pr-description**：根据分支的提交和 diff 写 PR 标题和描述（之前 / 之后 / 做法 / 测试），仓库有 PR 模板就按模板写。
- **issue-triage**：给没打标签的 issue 提出类型、优先级、重复项和缺信息的建议，只用仓库已有的标签，你确认后才会改。
- **repo-health**：给仓库打分（满分 100），检查文档、许可证、CI、测试、社区文件、误提交的密钥、大文件和活跃度，并列出最该先修的几项。
- **release-notes**：把上个版本以来的提交和 PR 整理成给用户看的更新日志（破坏性改动 / 新功能 / 修复 / 文档），并建议下一个版本号。你确认后才会发布。

安装：克隆仓库后运行 `./install.sh`，它会自动识别你装了 Claude Code 还是 Codex。也可以指定 `./install.sh claude`、`./install.sh codex` 或 `./install.sh all`。在 Codex 里输入 `$` 可以按名字选技能。

## Contributing

New skills are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
