# End-to-End Pipeline Test

## Overview

This test validates the complete ZenGlow data pipeline from wearable device sensor collection through to parent dashboard display and feedback processing.

## Test File

`__tests__/integration/end-to-end-pipeline.test.ts`

## Running the Test

```bash
# Run the specific end-to-end test
npm test __tests__/integration/end-to-end-pipeline.test.ts

# Run with verbose output
npm test __tests__/integration/end-to-end-pipeline.test.ts -- --verbose

# Run with coverage
npm run test:coverage __tests__/integration/end-to-end-pipeline.test.ts
```

## Test Structure

### Pipeline Stages Tested

1. **Wearable Sensor Data Collection**
   - Sensor data structure validation
   - Transport adapter functionality
   - Data buffering simulation

2. **Mobile App Data Transmission**
   - Payload structure validation
   - API transmission simulation
   - Invalid data handling

3. **Cloud AI Model Predictions**
   - Wellness prediction generation
   - Contextual recommendations
   - Real recommendation service integration

4. **Parent Dashboard Integration**
   - Dashboard data formatting
   - Feedback loop simulation
   - Alert generation

5. **Complete Pipeline Integration**
   - Full end-to-end data flow
   - Data integrity validation
   - Performance verification

## Test Data

The test uses realistic sample data including:

- **Sensor Readings**: Heart rate (85 bpm), stress level (0.75), activity level
- **Wellness Context**: Child age 8, morning scenarios, academic stress
- **Recommendation Context**: Low wellness score (35), downward trend
- **Parent Feedback**: Positive feedback on recommendations

## Expected Results

- ✅ All 9 test cases should pass
- ✅ Complete pipeline data flow validation
- ✅ Alert generation for high stress levels (>0.7)
- ✅ Recommendation generation based on wellness metrics
- ✅ Proper data structure validation throughout pipeline

## Test Output

The test provides detailed console logging showing:

```
🔄 Starting complete end-to-end pipeline test...
📱 Stage 1: Simulating wearable sensor data collection...
📲 Stage 2: Mobile app data transmission simulation...
☁️ Stage 3: Cloud AI model prediction generation...
👨‍👩‍👧‍👦 Stage 4: Parent dashboard data preparation...
✅ Pipeline validation: Checking end-to-end data integrity...
🎉 End-to-end pipeline test completed successfully!
```

## Dependencies

- Jest testing framework
- Existing ZenGlow sensor system
- Recommendation service
- Mock implementations for external services

## Documentation

For detailed test results and findings, see:
- [Test Results Documentation](../testing/END_TO_END_PIPELINE_TEST_RESULTS.md)

## Troubleshooting

If tests fail:

1. **Database Mock Issues**: Ensure expo-sqlite mocks are properly configured
2. **Import Errors**: Check that all ZenGlow modules are properly imported
3. **Type Errors**: Verify TypeScript interfaces match current implementation
4. **Service Unavailable**: Ensure recommendation service is available during test

## Contributing

When updating this test:

1. Keep tests focused on data flow validation
2. Use realistic sample data
3. Maintain proper mocking for external dependencies
4. Update documentation with any new test scenarios
5. Ensure test runs quickly (< 1 second) for CI/CD efficiency