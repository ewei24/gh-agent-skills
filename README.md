# gh-agent-skills

Agent skills for everyday GitHub chores. Drop them into Claude Code (or any agent that reads `SKILL.md` skills) and ask in plain language:

| Skill | Ask it | What it does |
|---|---|---|
| [`pr-description`](skills/pr-description/SKILL.md) | "write the PR description" | Reads your branch's commits and diff, writes a title and a Before / After / How / Testing body, follows the repo's PR template if it has one. |
| [`issue-triage`](skills/issue-triage/SKILL.md) | "triage the open issues" | Proposes type, priority, duplicates and needs-info for unlabeled issues using the repo's own labels, then applies only what you approve. |
| [`repo-health`](skills/repo-health/SKILL.md) | "give this repo a health check" | Scores the repo out of 100 (docs, license, CI, tests, community files, committed secrets, large files, activity) and lists the fixes that matter most. |

## Install

Claude Code, for all your projects:

```bash
git clone https://github.com/EthanWei-624/gh-agent-skills
mkdir -p ~/.claude/skills && cp -r gh-agent-skills/skills/* ~/.claude/skills/
```

For one project only, copy them into that project's `.claude/skills/` instead.

## Requirements

- `git` and `bash` for all skills
- Python 3.8+ for `repo-health` (standard library only, no network)
- [GitHub CLI](https://cli.github.com/) (`gh auth login`) for `issue-triage`, and for `pr-description` if you want it to create or edit the PR for you

## Usage

In Claude Code, just ask: "write the PR description for this branch", "triage the open issues", or "run a health check on this repo". The agent picks the matching skill.

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

- The skills never comment on, close, or relabel issues, or edit PRs, without your go-ahead.
- Issue and PR text from other people is treated as data, not instructions.
- `repo-health` reports where a secret is (file and line), never the secret itself.

## 中文说明

一组处理 GitHub 日常杂活的 agent 技能，放进 Claude Code 后直接用自然语言调用：

- **pr-description**：根据分支的提交和 diff 写 PR 标题和描述（之前 / 之后 / 做法 / 测试），仓库有 PR 模板就按模板写。
- **issue-triage**：给没打标签的 issue 提出类型、优先级、重复项和缺信息的建议，只用仓库已有的标签，你确认后才会改。
- **repo-health**：给仓库打分（满分 100），检查文档、许可证、CI、测试、社区文件、误提交的密钥、大文件和活跃度，并列出最该先修的几项。

安装方法见上面的 Install 部分。

## Contributing

New skills are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
