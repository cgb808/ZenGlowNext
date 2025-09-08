# Regenerating Assets

This document describes how to regenerate various build artifacts and assets that are excluded from version control to keep the repository clean.

## Coverage Reports

To regenerate test coverage reports:

```bash
npm test -- --coverage
```

Or use the dedicated script:

```bash
npm run test:coverage
```

This will generate:
- HTML coverage reports in `coverage/`
- LCOV format coverage data in `coverage/lcov.info`
- Coverage summary JSON in `coverage/coverage-summary.json`

The coverage reports are excluded from version control via `.gitignore` to prevent merge conflicts and keep the repository size manageable.

## Project Index

To regenerate the project structure index:

```bash
npm run generate-project-index
```

This creates `project-index.json` and `project-index.md` files with the current project structure.

## Docs Index

To regenerate documentation indexes:

```bash
npm run docs:index
```

This updates documentation cross-references and navigation.