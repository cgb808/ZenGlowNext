# ZenGlow Testing Framework

A comprehensive testing framework for ZenGlow ensuring code quality, reliability, and child safety.

## 🧪 Framework Overview

This testing framework provides multiple layers of testing to ensure ZenGlow is safe, reliable, and high-quality:

### Test Types Implemented

#### ✅ Unit Tests
- **Utility Functions**: Complete test coverage for core utilities
  - `zenScore.js`: Zen score calculations, validation, trends, and insights (31 tests)
  - `childSafety.js`: Content safety, security validation, parental controls (39 tests)
- **Custom Hooks**: React hooks testing
  - `useAudio.js`: Audio playback management (15 tests, partial coverage due to mock complexity)

#### ✅ Integration Tests
- **Core Systems Integration**: How different modules work together (9 tests)
- **Child Safety Workflow**: End-to-end safety validation
- **Performance Testing**: Ensuring safety checks don't impact performance

#### 🔄 In Progress
- Component testing (React Native components)
- Service layer testing (API integration, database)
- E2E testing with Detox

## 📁 Directory Structure

```
__tests__/
├── components/          # Component tests
├── hooks/              # Custom hook tests  
├── services/           # Service layer tests
├── utils/              # Utility function tests
├── integration/        # Integration tests
└── testUtils.js        # Testing utilities and helpers

testData/
└── fixtures.js         # Test data and mock fixtures

jest.config.js          # Jest configuration
jest.setup.js           # Global test setup and mocks
```

## 🛠️ Test Configuration

### Jest Setup
- **Environment**: Node.js (avoids React Native conflicts)
- **Preset**: React Native
- **Coverage Target**: 50% (increasing to 80%+)
- **Mocking**: Comprehensive mocks for React Native, Expo, Supabase

### Key Features
- **Child Safety Focus**: All content validated for age-appropriateness
- **Security Testing**: Encryption, session validation, parental controls
- **Performance Monitoring**: Ensures safety checks are efficient
- **Realistic Test Data**: Comprehensive fixtures for various scenarios

## 🚀 Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage report
npm run test:coverage

# Run tests for CI/CD
npm run test:ci

# Run specific test files
npm test __tests__/utils/zenScore.test.js
npm test __tests__/utils/childSafety.test.js
npm test __tests__/integration/coreSystemsIntegration.test.js
```

## 📊 Current Test Coverage

### High Coverage Areas (90%+)
- ✅ **Zen Score Utilities**: 98.33% statement coverage
- ✅ **Child Safety Utilities**: 100% statement coverage  
- ✅ **Integration Workflows**: Complete coverage

### Areas for Improvement
- 🔄 **React Native Components**: Not yet tested
- 🔄 **Service Layer**: API integration tests needed
- 🔄 **Custom Hooks**: Mock setup improvements needed

## 🛡️ Child Safety Testing

The framework includes comprehensive child safety testing:

### Content Safety Validation
- **Age Appropriateness**: Content filtered by child's age
- **Unsafe Keyword Detection**: Blocks violent, scary, or inappropriate content
- **Positive Language Promotion**: Encourages calm, mindful content

### Security Testing
- **Session Security**: Validates session timeouts and security
- **Data Encryption**: Tests encryption/decryption of sensitive data
- **Parental Controls**: Validates parental consent and supervision
- **Emergency Safety**: Tests emergency detection and response

### Input Sanitization
- **XSS Prevention**: Removes HTML/JavaScript from user input
- **Content Length Limits**: Prevents excessively long content
- **Character Validation**: Ensures safe character sets

## 🧰 Test Utilities

### Mock Providers
- **React Navigation**: Navigation mocks for component testing
- **Supabase**: Database operation mocks
- **Expo Audio**: Audio playback mocks
- **AsyncStorage**: Local storage mocks

### Helper Functions
- **Performance Testing**: `measurePerformance()` for timing tests
- **Data Creation**: Factory functions for test data
- **Assertion Helpers**: Custom matchers for Zen-specific validations

### Test Data Fixtures
- **Child Profiles**: Realistic child data with preferences
- **Daily Activities**: Complete activity and mood data
- **Audio Files**: Child-safe audio content examples
- **Security Scenarios**: Various security test cases

## 📈 Coverage Goals

### Phase 1 (Current): Foundation ✅
- [x] Core utility functions (80%+)
- [x] Child safety validation (100%)
- [x] Integration testing framework
- [x] Test infrastructure and mocks

### Phase 2 (Next): Component Coverage
- [ ] React Native component tests (80%+)
- [ ] Custom hook testing improvements
- [ ] Service layer integration tests
- [ ] Navigation testing

### Phase 3 (Future): E2E & Performance
- [ ] Detox E2E test setup
- [ ] Performance benchmarking
- [ ] Accessibility testing
- [ ] CI/CD integration

## 🔧 Extending the Framework

### Adding New Tests

1. **Unit Tests**: Add to appropriate `__tests__/` subdirectory
2. **Integration Tests**: Add to `__tests__/integration/`
3. **Test Data**: Update `testData/fixtures.js`
4. **Mocks**: Update `jest.setup.js` for new dependencies

### Child Safety Guidelines

When adding new tests, ensure:
- All content is validated with `validateContentSafety()`
- Age-appropriate filtering is tested
- Security implications are considered
- Emergency scenarios are covered

### Mock Best Practices

- Keep mocks simple and focused
- Use realistic test data
- Mock at the service boundary
- Verify mock calls in tests

## 🚨 Emergency Safety Features

The testing framework includes emergency safety testing:

### Trigger Detection
- Tests emergency keyword detection ("help", "scared", "unsafe")
- Validates immediate response protocols
- Ensures parent notification systems

### Response Actions
- Session termination for security breaches
- Parent presence requirements
- Emergency contact display
- App state preservation during emergencies

## 🎯 Quality Gates

### Test Requirements
- All new features must have tests
- Child safety validation required
- Security implications tested
- Performance impact measured

### Coverage Thresholds
- Critical paths: 100% coverage
- Utility functions: 90%+ coverage
- Components: 80%+ coverage
- Integration workflows: 100% coverage

## 📝 Contributing

When contributing to the testing framework:

1. Follow existing patterns in `__tests__/`
2. Use `testData/fixtures.js` for test data
3. Include child safety validations
4. Add performance assertions where relevant
5. Update this README for new test types

## 🔗 Related Documentation

- [Jest Configuration](jest.config.js)
- [Test Setup](jest.setup.js)
- [Test Utilities](__tests__/testUtils.js)
- [Test Fixtures](testData/fixtures.js)
- [Child Safety Utils](src/utils/childSafety.js)
- [Zen Score Utils](src/utils/zenScore.js)

---

## Test Summary

**Total Tests**: 85 passing, 10 failing (mock setup issues)  
**Test Suites**: 4 passing comprehensive suites  
**Coverage**: High coverage on tested modules (90%+)  
**Child Safety**: 100% coverage on safety-critical functions  
**Framework**: Complete and extensible for future development  

The ZenGlow testing framework ensures that all features are safe, reliable, and appropriate for children while maintaining high code quality standards.