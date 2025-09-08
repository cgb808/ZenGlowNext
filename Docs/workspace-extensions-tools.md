# Workspace Extensions, Tools, Plugins, and MCP Servers

This document lists all major VS Code extensions, plugins, tools, and MCP servers that can be used to manipulate, analyze, or enhance this workspace, along with a brief explanation and common commands or use cases.

---

## Extensions & Plugins

### 1. IntelliCode

- **ID:** `visualstudioexptteam.vscodeintellicode`
- **Use:** AI-assisted code completions and recommendations.
- **Commands:**
  - Suggestions appear automatically as you type.

### 2. IntelliCode API Usage Examples

- **ID:** `visualstudioexptteam.intellicode-api-usage-examples`
- **Use:** Shows relevant code examples from GitHub for APIs.
- **Commands:**
  - Hover over API usage to see examples.

### 3. Docker

- **ID:** `ms-azuretools.vscode-docker`
- **Use:** Manage, build, and debug Docker containers.
- **Commands:**
  - `Docker: Build Image`
  - `Docker: Run` / `Attach` / `Compose Up`

### 4. Dev Containers

- **ID:** `ms-vscode-remote.remote-containers`
- **Use:** Open the workspace in a Docker-based development container.
- **Commands:**
  - `Remote-Containers: Open Folder in Container`

---

## MCP Servers

- **GoCodeo MCP**
  - **Use:** Model Context Protocol server for real-time, context-aware actions and automation.
  - **Commands:**
    - Managed by GoCodeo plugin, typically auto-started.

- **VSCode MCP Server**
  - **ID:** `semanticworkbenchteam.mcp-server-vscode` (or similar)
  - **Use:** Exposes VS Code as an MCP server for LLM/AI integration.
  - **Commands:**
    - `MCP: Start Server`
    - `MCP: Stop Server`

---

## Other Tools/Plugins

- **GitHub Copilot**
  - **Use:** AI code completions, chat, and test generation.
  - **Commands:**
    - Suggestions as you type, `/copilot` chat commands.

- **React Native Tools**
  - **Use:** Debug and test React Native apps.
  - **Commands:**
    - `React Native: Run Android/iOS`

- **GitLens**
  - **Use:** Git commit history, blame, and repository insights.
  - **Commands:**
    - `GitLens: Show Commit Details`

---

## Code Quality, Linting, Formatting, and Validation Tools

### ESLint

- **Use:** Lint JavaScript/TypeScript code for style and errors.
- **Commands:**
  - `npm run lint` (check)
  - `npm run lint:fix` (auto-fix)

### Prettier

- **Use:** Format code for consistent style.
- **Commands:**
  - `npm run format` (format all)
  - `npm run format:check` (check only)

### Markdownlint

- **Use:** Lint Markdown files for style and consistency.
- **Commands:**
  - `npm run lint:md` (check)
  - `npm run lint:md:fix` (auto-fix)

### TypeScript Type Checking

- **Use:** Check for type errors in TS/TSX files.
- **Commands:**
  - `npm run type-check`

### YAML Validation

- **Use:** Validate all YAML/YML files in the project.
- **Commands:**
  - `npm run yaml:validate`

### YAML Companion Generation

- **Use:** Generate YAML sidecar/companion files for project files.
- **Commands:**
  - `npm run yaml:generate`

### Schema Validation

- **Use:** Run custom schema validation scripts.
- **Commands:**
  - `npm run schema:validate`

### Project Health Analyzer

- **Use:** Analyze project health and structure.
- **Commands:**
  - `npm run health:analyze`
  - `npm run health:quick`

### Refactor Large Files

- **Use:** Identify and plan refactoring for large files.
- **Commands:**
  - `npm run refactor:large-files`
  - `npm run refactor:plan`

### Jest (Testing)

- **Use:** Run unit and integration tests.
- **Commands:**
  - `npm run test`

### All-in-One Quality/Validation

- **Use:** Run all major checks in one command.
- **Commands:**
  - `npm run quality`
  - `npm run validate`

- **Jupyter**
  - **Use:** Interactive notebooks for data science and visualization.
  - **Commands:**
    - `Jupyter: Create New Notebook`

---

## How to Use

- Install extensions from the VS Code Marketplace.
- Use the Command Palette (`Ctrl+Shift+P`) to run extension commands.
- MCP servers are typically managed by their respective extensions or plugins.

---

_Update this file as new tools or extensions are added to the workspace._
