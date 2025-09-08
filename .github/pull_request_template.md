---
name: Pull Request
about: Template for all pull requests
title: ''
labels: ''
assignees: ''
---

## 📝 Description

<!-- Provide a clear and concise description of your changes -->

## 🔗 Related Issue

<!-- Link to the issue this PR addresses -->
Fixes #<!-- issue number -->

## 🧪 Type of Change

<!-- Check all that apply -->
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that causes existing functionality to change)
- [ ] 📚 Documentation update
- [ ] 🔒 Security improvement
- [ ] 🎨 UI/UX improvement
- [ ] ⚡ Performance improvement
- [ ] 🧹 Code refactoring

## ✅ Checklist

### Code Quality
- [ ] **Tests added/updated** for new functionality
- [ ] **All tests pass** (`npm test`)
- [ ] **Linting passes** (`npm run lint`)
- [ ] **Type checking passes** (`npm run typecheck`)
- [ ] **Code follows established patterns** and style guidelines

### Documentation
- [ ] **Documentation updated** for new features
- [ ] **README updated** if installation/setup changed
- [ ] **Project index regenerated** if structure changed (`npm run docs:index`)
- [ ] **Environment variables documented** in `.env.example`

### Security & Child Safety
- [ ] **No secrets committed** (checked `.env` usage)
- [ ] **Child safety validation** implemented where applicable
- [ ] **Security implications assessed** for child-facing features
- [ ] **COPPA compliance maintained** for data handling

### Performance & Size
- [ ] **Bundle size impact assessed** (`npm run check:deps`)
- [ ] **Large files properly handled** (see [Large File Policy](./CONTRIBUTING.md#large-file-policy))
- [ ] **Performance impact tested** on target devices
- [ ] **Memory usage considered** for long-running sessions

## 🧪 Testing

<!-- Describe how you tested your changes -->

### Test Environment
- [ ] **iOS Simulator** (version: ___)
- [ ] **Android Emulator** (API level: ___)
- [ ] **Physical Device** (device: ___)
- [ ] **Web Browser** (browser: ___)

### Test Scenarios
<!-- Describe specific test cases you ran -->
- [ ] **Happy path**: Core functionality works as expected
- [ ] **Edge cases**: Boundary conditions handled
- [ ] **Error scenarios**: Graceful error handling
- [ ] **Child safety**: Age-appropriate content validation
- [ ] **Accessibility**: Screen reader and keyboard navigation

## 📸 Screenshots/Videos

<!-- If applicable, add screenshots or videos to demonstrate changes -->

### Before
<!-- Screenshot/description of current behavior -->

### After
<!-- Screenshot/description of new behavior -->

## 🔒 Security Considerations

<!-- For any security-related changes -->
- [ ] **Data privacy**: User data handling reviewed
- [ ] **Input validation**: All inputs properly sanitized
- [ ] **Authentication**: Security boundaries maintained
- [ ] **Child protection**: Additional safety measures implemented
- [ ] **Vulnerability assessment**: Potential risks identified and mitigated

## 📱 Platform Testing

<!-- Test results across platforms -->
| Platform | Status | Notes |
|----------|--------|-------|
| iOS      | ✅/❌   |       |
| Android  | ✅/❌   |       |
| Web      | ✅/❌   |       |

## 🧠 AI/ML Impact

<!-- If your changes affect AI/ML components -->
- [ ] **Model compatibility**: Changes compatible with existing models
- [ ] **Data pipeline**: Training/inference pipelines updated
- [ ] **Performance metrics**: Model performance maintained/improved
- [ ] **Child safety models**: Safety validation models updated

## 📋 Additional Notes

<!-- Any additional information, concerns, or context -->

## 🔍 Reviewer Focus Areas

<!-- Highlight specific areas that need extra attention during review -->
- [ ] **Security review needed**: Child safety implementations
- [ ] **Performance review needed**: Core component changes
- [ ] **Accessibility review needed**: UI/UX changes
- [ ] **Architecture review needed**: Structural changes

---

### For Reviewers

Please ensure:
1. **Child safety** is prioritized in all reviews
2. **Security implications** are thoroughly assessed
3. **Performance impact** is evaluated
4. **COPPA compliance** is maintained
5. **Code quality** meets project standards

**Thank you for contributing to ZenGlow! 🌙✨**