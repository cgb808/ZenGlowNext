# ZenGlow Documentation Index

- **Main README**: [../README.md](../README.md) - Getting started and release process
- API Documentation: [Docs/api/API_DOCUMENTATION.md](api/API_DOCUMENTATION.md)
- Architecture Details (Flask Backend): [Docs/backend/FLASK_BACKEND_ARCHITECTURE.md](backend/FLASK_BACKEND_ARCHITECTURE.md)
- **RAG Pipeline Architecture**: [Docs/rag-pipeline.md](rag-pipeline.md)
- Project Outline: [Docs/project/PROJECT_OUTLINE.md](project/PROJECT_OUTLINE.md)
- Wearable Sensor Integration: [Docs/WEARABLE_SENSOR_INTEGRATION.md](WEARABLE_SENSOR_INTEGRATION.md)
- ZenGlow Audio Guide: [Docs/AUDIO_GUIDE.md](AUDIO_GUIDE.md)
- CHANGELOG.md: [../CHANGELOG.md](../CHANGELOG.md)
- AI Model Architecture for ZenGlow: [Docs/COMPLETE_AI_ECOSYSTEM.md](COMPLETE_AI_ECOSYSTEM.md)
- ZenGlow App Dependencies: [Docs/dependencies.md](dependencies.md)
- development-snippets.md: [Docs/development-snippets.md](development-snippets.md)
- EnhancedZenMoonAvatar: [Docs/EnhancedZenMoonAvatar.md](EnhancedZenMoonAvatar.md)
- Environment setup: [Docs/ENV_SETUP.md](ENV_SETUP.md)
- exerciseSchema.js: [Docs/exerciseSchema.md](exerciseSchema.md)
- FaceComponents: [Docs/FaceComponents.md](FaceComponents.md)
- Focus Exercises Schema and Library: [Docs/focusExercises.md](focusExercises.md)
- Housekeeping: Irrelevant/Unused Files & Directory Structure: [Docs/housekeeping-tasks.md](housekeeping-tasks.md)
- 📱 ZenGlow Mobile Setup Guide: [Docs/mobile-setup.md](mobile-setup.md)
- **🔍 Observability & Logging Guide: [Docs/observability.md](observability.md)**
- Parent-Child Tagalong System - Implementation Guide: [Docs/ParentChildTagalong_Implementation.md](ParentChildTagalong_Implementation.md)
- Parent Dashboard Module: [Docs/ParentDashboard_README.md](ParentDashboard_README.md)
- Self-Improving Wellness Companion Pipeline — Supplemental Overview: [Docs/project/SELF_IMPROVING_PIPELINE_OVERVIEW.md](project/SELF_IMPROVING_PIPELINE_OVERVIEW.md)
- ZenGlow Documentation Index: [Docs/README.md](README.md)
- Security Implementation Guide for ZenGlow Sync: [Docs/Security_Implementation_Guide.md](Security_Implementation_Guide.md)
- ZenGlow Sound Library Placeholders: [Docs/SoundLibraryPlaceholders.md](SoundLibraryPlaceholders.md)
- Supabase Integration Setup Guide: [Docs/supabase-setup.md](supabase-setup.md)
- UI and Companion AI Interaction: [Docs/UI_COMPANION_ARCHITECTURE.md](UI_COMPANION_ARCHITECTURE.md)
- Workspace Extensions, Tools, Plugins, and MCP Servers: [Docs/workspace-extensions-tools.md](workspace-extensions-tools.md)
- ZenGlow Workspace Audit: Incomplete & Unfinished Work: [Docs/workspace-incomplete-audit.md](workspace-incomplete-audit.md)
- WSL Graphics & ZenGlow Development Guide: [Docs/wsl-graphics-guide.md](wsl-graphics-guide.md)
- WSL + Ubuntu Server Setup for ZenGlow Local Development: [Docs/wsl-setup.md](wsl-setup.md)
- ZenGlowCompanion Documentation: [Docs/ZenGlowCompanion.md](ZenGlowCompanion.md)
- ZenMoonAvatar.md: [Docs/ZenMoonAvatar.md](ZenMoonAvatar.md)
- ZenSoundProvider - Enhanced for ZenMoon Integration: [Docs/ZenSoundProvider.md](ZenSoundProvider.md)
- ZFS Optimization for ZenGlow Development: [Docs/zfs-optimization.md](zfs-optimization.md)

# Supabase CLI

[![Coverage Status](https://coveralls.io/repos/github/supabase/cli/badge.svg?branch=main)](https://coveralls.io/github/supabase/cli?branch=main) [![Bitbucket Pipelines](https://img.shields.io/bitbucket/pipelines/supabase-cli/setup-cli/master?style=flat-square&label=Bitbucket%20Canary)](https://bitbucket.org/supabase-cli/setup-cli/pipelines) [![Gitlab Pipeline Status](https://img.shields.io/gitlab/pipeline-status/sweatybridge%2Fsetup-cli?label=Gitlab%20Canary)
](https://gitlab.com/sweatybridge/setup-cli/-/pipelines)

[Supabase](https://supabase.io) is an open source Firebase alternative. We're building the features of Firebase using enterprise-grade open source tools.

This repository contains all the functionality for Supabase CLI.

- [x] Running Supabase locally
- [x] Managing database migrations
- [x] Creating and deploying Supabase Functions
- [x] Generating types directly from your database schema
- [x] Making authenticated HTTP requests to [Management API](https://supabase.com/docs/reference/api/introduction)

## Getting started

### Install the CLI

Available via [NPM](https://www.npmjs.com) as dev dependency. To install:

```bash
npm i supabase --save-dev
```

To install the beta release channel:

```bash
npm i supabase@beta --save-dev
```

When installing with yarn 4, you need to disable experimental fetch with the following nodejs config.

```
NODE_OPTIONS=--no-experimental-fetch yarn add supabase
```

> **Note**
> For Bun versions below v1.0.17, you must add `supabase` as a [trusted dependency](https://bun.sh/guides/install/trusted) before running `bun add -D supabase`.

<details>
  <summary><b>macOS</b></summary>

Available via [Homebrew](https://brew.sh). To install:

```sh
brew install supabase/tap/supabase
```

To install the beta release channel:

```sh
brew install supabase/tap/supabase-beta
brew link --overwrite supabase-beta
```

To upgrade:

```sh
brew upgrade supabase
```

</details>

<details>
  <summary><b>Windows</b></summary>

Available via [Scoop](https://scoop.sh). To install:

```powershell
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

To upgrade:

```powershell
scoop update supabase
```

</details>

<details>
  <summary><b>Linux</b></summary>

Available via [Homebrew](https://brew.sh) and Linux packages.

#### via Homebrew

To install:

```sh
brew install supabase/tap/supabase
```

To upgrade:

```sh
brew upgrade supabase
```

#### via Linux packages

Linux packages are provided in [Releases](https://github.com/supabase/cli/releases). To install, download the `.apk`/`.deb`/`.rpm`/`.pkg.tar.zst` file depending on your package manager and run the respective commands.

```sh
sudo apk add --allow-untrusted <...>.apk
```

```sh
sudo dpkg -i <...>.deb
```

```sh
sudo rpm -i <...>.rpm
```

```sh
sudo pacman -U <...>.pkg.tar.zst
```

</details>

<details>
  <summary><b>Other Platforms</b></summary>

You can also install the CLI via [go modules](https://go.dev/ref/mod#go-install) without the help of package managers.

```sh
go install github.com/supabase/cli@latest
```

Add a symlink to the binary in `$PATH` for easier access:

```sh
ln -s "$(go env GOPATH)/bin/cli" /usr/bin/supabase
```

This works on other non-standard Linux distros.

</details>

<details>
  <summary><b>Community Maintained Packages</b></summary>

Available via [pkgx](https://pkgx.sh/). Package script [here](https://github.com/pkgxdev/pantry/blob/main/projects/supabase.com/cli/package.yml).
To install in your working directory:

```bash
pkgx install supabase
```

Available via [Nixpkgs](https://nixos.org/). Package script [here](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/tools/supabase-cli/default.nix).

</details>

### Run the CLI

```bash
supabase bootstrap
```

Or using npx:

```bash
npx supabase bootstrap
```

The bootstrap command will guide you through the process of setting up a Supabase project using one of the [starter](https://github.com/supabase-community/supabase-samples/blob/main/samples.json) templates.

## Docs

Command & config reference can be found [here](https://supabase.com/docs/reference/cli/about).

## Breaking changes

We follow semantic versioning for changes that directly impact CLI commands, flags, and configurations.

However, due to dependencies on other service images, we cannot guarantee that schema migrations, seed.sql, and generated types will always work for the same CLI major version. If you need such guarantees, we encourage you to pin a specific version of CLI in package.json.

## Developing

To run from source:

```sh
# Go >= 1.22
go run . help
```
