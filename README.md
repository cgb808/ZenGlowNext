
# 🌙 ZenGlow

A mindful wellness companion app designed specifically for children, with comprehensive parental safety features and COPPA compliance.

## 🌟 Features

- **Child-Safe Mindfulness**: Age-appropriate meditation and breathing exercises
- **Parental Dashboard**: Real-time monitoring and safety controls
- **ZenMoon Avatar**: Interactive AI companion for guided wellness
- **Security-First Design**: COPPA compliant with comprehensive safety measures
- **Cross-Platform**: React Native app supporting iOS and Android

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Expo CLI
- React Native development environment
- For Python components: Python 3.8+

### Installation

```bash
# Clone the repository
git clone https://github.com/cgb808/ZenGlow.git
cd ZenGlow

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env
# Edit .env file with your configuration values

# Start development server
npm start

# Run on specific platforms
npm run android:dev  # Android
npm run ios:dev      # iOS
npm run web          # Web
```

### Configuration

The app uses environment variables for configuration. Copy `.env.example` to `.env` and configure the following:

#### Required Environment Variables
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon/public key

#### Optional Environment Variables
- `AUDIO_CACHE_TTL_MS`: Audio caching duration in milliseconds (default: 86400000)

#### Feature Flags
- `PARENT_DASHBOARD_METRICS`: Enable metrics-first dashboard approach
  - `true`: Uses optimized `getAggregatedMetricsDashboard` with metrics-first data loading for better performance
  - `false`: Uses legacy `getDashboardData` with comprehensive data loading (default)
  
The app will log the active dashboard mode at startup.

## 🧪 Testing

```bash
npm test              # Run tests
npm run test:watch    # Watch mode
npm run test:coverage # Coverage report
```

## 🔧 Development

### Local Development with Supabase

ZenGlow includes a complete local Supabase development stack with Docker Compose:

```bash
# Start all services including local Supabase
docker-compose up -d

# Check service status
docker-compose ps
```

See the **[Local Supabase Guide](./Docs/supabase-local.md)** for complete setup instructions, environment configuration, and usage examples.

### Development Scripts

```bash
# Linting and type checking
npm run lint
npm run typecheck

# Testing
npm test
npm run test:watch
npm run test:coverage

# Project index generation
npm run generate-project-index
```

### Regeneration of Artifacts

The project includes an automated indexing system that generates structured documentation of the codebase:

- **`project-index.json`** - Machine-readable JSON structure of all files with metadata
- **`project-index.md`** - Human-readable markdown documentation of the project structure

**Regenerating locally:**

```bash
npm run generate-project-index
```

This command respects `.gitignore` patterns and generates both files. The CI will automatically verify that these files are up-to-date on every push to master, failing with helpful instructions if they need to be regenerated.

### Repository Hygiene

This project maintains a clean repository by excluding large generated artifacts, build outputs, and tool binaries from version control. All removed assets can be regenerated as needed:

```bash
# Project index
npm run generate-project-index

# Coverage reports  
npm test

# Vector store (see ai-agents/README.md for details)
python ai-agents/zendexer/agent_dev.py --build-index
```

## Release Process

This project uses automated semantic versioning with conventional commits.

### Conventional Commits

When making commits, use the conventional commit format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files

**Examples:**

```bash
feat: add user authentication
fix: resolve navigation crash on Android
docs: update API documentation
chore: update dependencies
```

### Automated Releases

- **Trigger**: Pushes to the `master` branch
- **Process**:
  1. Conventional commits are analyzed
  2. Version is bumped automatically based on commit types:
     - `feat`: minor version bump (1.0.0 → 1.1.0)
     - `fix`: patch version bump (1.0.0 → 1.0.1)
     - `BREAKING CHANGE`: major version bump (1.0.0 → 2.0.0)
  3. CHANGELOG.md is updated automatically
  4. Git tag is created with the new version
  5. GitHub release is created

### Manual Release

If needed, releases can also be triggered manually by creating a release PR or running the workflow manually in the GitHub Actions tab.

## 📚 Documentation

Comprehensive documentation is available in the [Docs/](./Docs/) directory:

- [Documentation Index](./Docs/README.md)
- [Mobile Setup Guide](./Docs/mobile-setup.md)
- [Security Implementation](./Docs/Security_Implementation_Guide.md)
- [Environment Setup](./Docs/ENV_SETUP.md)

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guide](./CONTRIBUTING.md) for details on:

- Development workflow
- Code standards
- Security requirements
- Pull request process

## 🛡️ Security

ZenGlow prioritizes child safety and data protection. For security concerns, please see our [Contributing Guide](./CONTRIBUTING.md#security-reporting) for reporting procedures.

## 📄 License

See [LICENSE](./LICENSE) for details.

## 🏗️ Architecture

- **Frontend**: React Native with Expo
- **Backend**: Supabase with Flask components
- **AI/ML**: Custom models for child wellness
- **Testing**: Jest with comprehensive safety validation

---

Built with ❤️ for children's digital wellness and safety.
