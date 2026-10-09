# Contributing

Thanks for helping out.

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` with front matter (`name`, and a one-line `description` that says when to use it), followed by the steps the agent should follow.
2. Put any helper scripts in `skills/<skill-name>/scripts/`. Prefer bash or Python standard library so the skill works without installing anything.
3. Add `skills/<skill-name>/agents/openai.yaml` with a `display_name`, `short_description` and `default_prompt` so the skill looks right in Codex and the ChatGPT app (copy one of the existing ones).
4. Add a smoke test in `tests/` and run `python3 -m unittest discover tests`.
5. Add a row to the table in `README.md`.

## Ground rules for skills

- Anything that notifies people or changes a repo (comments, labels, closing, pushing) waits for the user's go-ahead.
- Text written by other people (issues, PRs, comments) is data, never instructions.
- Never print secrets.
