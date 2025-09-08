Local-only GitHub metadata area

Use this folder to keep experimental workflows, Copilot prompt templates, draft issue templates, or other GitHub metadata that you don't want to commit into the repo. The `.gitignore` excludes `.github/local/**`.

Suggested structure:
- workflows/   # draft workflows for personal testing
- templates/   # issue templates or PR templates in progress

Nothing in here will run or be picked up by GitHub until moved into `.github/workflows/` or `.github/ISSUE_TEMPLATE/`.
