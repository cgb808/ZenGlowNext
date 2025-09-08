# Code Assistant Tooling

This project is configured to work smoothly with AI/code assistant tools (GitHub Copilot, etc.) and automated formatting.

## Editor & Formatting

- Prettier config: root `.prettierrc`
- ESLint (flat config): `eslint.config.cjs`
- EditorConfig: `.editorconfig` ensures whitespace consistency
- Recommended extensions: `.vscode/extensions.json`

### Commands

```
npm run lint        # report issues
npm run lint:fix    # auto-fix where possible
npm run format      # format all supported files
npm run format:check# verify formatting (CI friendly)
npm run typecheck   # TypeScript type checking
```

## Assistant Guidance

When using an AI assistant for code edits:

1. Prefer incremental, small commits.
2. Run `npm run lint:fix` after large refactors.
3. Keep generated artifacts (models, large data) out of git—see `.gitignore`.
4. For new config/rules, document rationale in commit body.

## Adding New Tooling

If you introduce a new static analysis or formatting tool, add:

- Config file at repo root
- Script entries in `package.json`
- A brief section here

## Future Enhancements

- Auto-run lint & format on pre-commit (husky) – intentionally deferred until rules stabilize.
- AI prompt templates for common refactors.
