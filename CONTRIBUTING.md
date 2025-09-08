# Contributing to ZenGlow

Thank you for your interest in contributing to ZenGlow! This guide will help you get started with our development workflow and standards.

## 📋 Prerequisites

### Required Software
- **Node.js** 18+ with npm
- **Expo CLI** (`npm install -g @expo/cli`)
- **Git** with proper configuration
- **Code Editor** with TypeScript support (VS Code recommended)

### Development Environment
- **React Native Environment**: Follow [React Native Environment Setup](https://reactnative.dev/docs/environment-setup)
- **iOS Development**: Xcode 14+ (macOS only)
- **Android Development**: Android Studio with SDK 33+
- **Python Environment**: Python 3.8+ for AI/ML components

### Getting Started
```bash
# Clone and setup
git clone https://github.com/cgb808/ZenGlow.git
cd ZenGlow
npm install

# Verify setup
npm run typecheck
npm test
npm run lint
```

## 🌿 Branching Strategy

### Branch Naming Convention
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `security/description` - Security-related changes
- `refactor/description` - Code refactoring

### Workflow
1. **Create branch** from `main`: `git checkout -b feature/your-feature`
2. **Make changes** with frequent commits
3. **Update project index** if structure changed: `npm run docs:index`
4. **Test thoroughly**: `npm test && npm run lint && npm run typecheck`
5. **Push and create PR** against `main`

## 📝 Commit Style

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `security`: Security improvements
- `perf`: Performance improvements

### Examples
```bash
feat(avatar): add new ZenMoon expressions
fix(auth): resolve parent authentication issue
docs(setup): update installation instructions
security(validation): enhance input sanitization
```

## ✅ Pull Request Checklist

Before submitting a PR, ensure:

### Code Quality
- [ ] **Tests added/updated** for new functionality
- [ ] **All tests pass**: `npm test`
- [ ] **Linting passes**: `npm run lint`
- [ ] **Type checking passes**: `npm run typecheck`
- [ ] **Code follows established patterns**

### Documentation
- [ ] **Documentation updated** for new features
- [ ] **README updated** if installation/setup changed
- [ ] **Project index regenerated** if structure changed: `npm run docs:index`
- [ ] **Environment variables documented** in `.env.example`

### Security & Safety
- [ ] **No secrets committed** (use `.env` files)
- [ ] **Child safety validation** implemented where applicable
- [ ] **Security implications assessed** for child-facing features
- [ ] **COPPA compliance maintained**

### Size & Performance
- [ ] **Bundle size impact assessed** (use `npm run check:deps`)
- [ ] **Large files properly handled** (see Large File Policy below)
- [ ] **Performance impact tested** on lower-end devices

## 🎯 Code Standards

### JavaScript/TypeScript

#### Style Guidelines
- **ESLint configuration**: Follow `.eslintrc.js` rules
- **Prettier formatting**: Auto-format with `npm run format`
- **TypeScript**: Strict mode enabled, avoid `any` types
- **Imports**: Use absolute imports via path mapping

#### Best Practices
```typescript
// ✅ Good: Proper typing and error handling
interface ZenScoreData {
  score: number;
  timestamp: Date;
  childId: string;
}

const calculateZenScore = async (childId: string): Promise<ZenScoreData> => {
  try {
    const data = await fetchChildData(childId);
    return {
      score: computeScore(data),
      timestamp: new Date(),
      childId
    };
  } catch (error) {
    logger.error('Failed to calculate zen score', { childId, error });
    throw new ZenScoreError('Calculation failed');
  }
};

// ❌ Avoid: Untyped, no error handling
const getScore = (id) => {
  const data = fetchChildData(id);
  return data.score;
};
```

#### Child Safety Requirements
All child-facing code must:
- Validate content safety with `validateContentSafety()`
- Include age-appropriate filtering
- Handle emergency scenarios
- Log security-relevant events

### Python Standards

#### Style Guidelines
- **PEP 8 compliance**: Follow Python style guide
- **Type hints**: Use type annotations for all functions
- **Docstrings**: Document all public functions/classes
- **Error handling**: Comprehensive exception handling

#### Example
```python
from typing import Dict, List, Optional
import logging

def analyze_child_interaction(
    interaction_data: Dict[str, Any],
    child_age: int
) -> Optional[Dict[str, float]]:
    """
    Analyze child interaction data for wellness metrics.
    
    Args:
        interaction_data: Raw interaction metrics
        child_age: Child's age for appropriate filtering
        
    Returns:
        Processed wellness metrics or None if invalid
        
    Raises:
        ValidationError: If data fails safety validation
    """
    try:
        if not validate_child_data_safety(interaction_data, child_age):
            raise ValidationError("Data failed safety validation")
            
        metrics = process_wellness_data(interaction_data)
        return apply_age_appropriate_filtering(metrics, child_age)
        
    except Exception as e:
        logging.error(f"Child interaction analysis failed: {e}")
        return None
```

## 📦 Large File Policy

### File Size Guidelines
- **Source files**: < 500 lines (consider refactoring larger files)
- **Assets**: 
  - Images: < 2MB each, use compressed formats
  - Audio: < 5MB each, use compressed formats
  - Videos: < 10MB each, consider external hosting
- **Dependencies**: Justify additions > 100KB

### Asset Management
```bash
# Check large files before commit
npm run refactor:large-files

# Optimize images
# Use tools like imagemin or online compression

# Audio/Video assets
# Store large media in external CDN if > 5MB
# Reference via environment variables
```

### Git LFS Usage
For files > 10MB:
```bash
# Track large files with Git LFS
git lfs track "*.mp4"
git lfs track "*.zip"
git add .gitattributes
```

## 🔒 Security Reporting

### Reporting Security Issues
**DO NOT** open public issues for security vulnerabilities.

#### For Security Issues:
1. **Email**: security@zenglow.app (if available)
2. **GitHub Security**: Use GitHub's private security reporting
3. **Include**:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact on child safety
   - Suggested fix (if known)

#### Child Safety Priority
- Report **immediately** if children could be at risk
- Include **severity assessment** for COPPA compliance
- Provide **emergency contact** information if critical

### Security Best Practices
- **Never commit secrets**: Use environment variables
- **Validate all inputs**: Especially child-provided data
- **Log security events**: Use structured logging
- **Regular updates**: Keep dependencies current
- **Code review**: Security-focused review for all PRs

## 🔄 Updating Project Index

The project index (`project-index.json`) tracks our codebase structure:

### When to Update
- Adding new files/directories
- Removing files/directories  
- Changing file purposes
- Restructuring components

### How to Update
```bash
# Regenerate project index
npm run docs:index

# Verify changes
git diff project-index.json

# Commit with your changes
git add project-index.json
git commit -m "chore: update project index for new components"
```

### Manual Updates
For complex changes, edit `project-index.json` directly:
```json
{
  "src/components/NewComponent": {
    "type": "component",
    "description": "New child safety component",
    "dependencies": ["src/utils/childSafety"],
    "tests": ["__tests__/components/NewComponent.test.tsx"]
  }
}
```

## 🧪 Testing Guidelines

### Test Categories
1. **Unit Tests**: Individual component/function testing
2. **Integration Tests**: Component interaction testing
3. **Child Safety Tests**: COPPA compliance validation
4. **Security Tests**: Vulnerability and data protection testing

### Writing Tests
```typescript
// Component test example
import { render, fireEvent } from '@testing-library/react-native';
import { ZenMoonAvatar } from '../ZenMoonAvatar';
import { validateContentSafety } from '@/utils/childSafety';

describe('ZenMoonAvatar', () => {
  it('should validate content safety before display', async () => {
    const { getByTestId } = render(
      <ZenMoonAvatar content="test content" />
    );
    
    expect(validateContentSafety).toHaveBeenCalledWith("test content");
  });
  
  it('should handle emergency scenarios', async () => {
    const onEmergency = jest.fn();
    const { getByTestId } = render(
      <ZenMoonAvatar onEmergency={onEmergency} />
    );
    
    fireEvent.press(getByTestId('emergency-button'));
    expect(onEmergency).toHaveBeenCalled();
  });
});
```

## 🎨 UI/UX Guidelines

### Child-Friendly Design
- **Large touch targets**: Minimum 44px for accessibility
- **Clear visual feedback**: Immediate response to interactions
- **Age-appropriate colors**: Calming, non-stimulating palette
- **Simple navigation**: Intuitive for young users

### Accessibility
- **Screen reader support**: Proper ARIA labels
- **High contrast**: WCAG AA compliance
- **Font scaling**: Support dynamic type sizes
- **Motor accessibility**: Alternative input methods

## 📞 Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Documentation**: Check [Docs/](./Docs/) directory first

### Code Review
- **Required reviewers**: Minimum 1 reviewer for PRs
- **Security review**: Required for child-facing features
- **Performance review**: Required for core components

### Development Support
- **Setup issues**: Check [mobile-setup.md](./Docs/mobile-setup.md)
- **Environment problems**: See [ENV_SETUP.md](./Docs/ENV_SETUP.md)
- **Testing help**: Review [__tests__/README.md](./__tests__/README.md)

---

Thank you for contributing to ZenGlow! Together, we're building a safer digital wellness experience for children. 🌙✨