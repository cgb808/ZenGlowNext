/**
 * Tests for Error Boundary integration with centralized logging
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { Text } from 'react-native';
import { logger } from '../../src/lib/logging';
import { AppErrorBoundary, CompanionErrorBoundary } from '../../app/_layout';

// Mock the logger
jest.mock('../../src/lib/logging', () => ({
  logger: {
    error: jest.fn(),
    warn: jest.fn(),
  },
}));

const mockedLogger = logger as jest.Mocked<typeof logger>;

// Component that throws an error for testing
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <Text>No error</Text>;
};

beforeEach(() => {
  jest.clearAllMocks();
  // Suppress console.error for these tests
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('AppErrorBoundary', () => {
  it('should catch errors and log them with centralized logging', () => {
    render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(mockedLogger.error).toHaveBeenCalledWith(
      'App Error Boundary caught an error',
      expect.objectContaining({
        error: expect.objectContaining({
          name: 'Error',
          message: 'Test error',
          stack: expect.any(String),
        }),
        errorInfo: expect.objectContaining({
          componentStack: expect.any(String),
        }),
        boundary: 'AppErrorBoundary',
      })
    );
  });

  it('should display error UI when error occurs', () => {
    const { getByText } = render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(getByText('Something went wrong')).toBeTruthy();
    expect(getByText('Test error')).toBeTruthy();
  });

  it('should not log when no error occurs', () => {
    render(
      <AppErrorBoundary>
        <ThrowError shouldThrow={false} />
      </AppErrorBoundary>
    );

    expect(mockedLogger.error).not.toHaveBeenCalled();
  });
});

describe('CompanionErrorBoundary', () => {
  it('should catch errors and log them with warn level', () => {
    render(
      <CompanionErrorBoundary>
        <ThrowError />
      </CompanionErrorBoundary>
    );

    expect(mockedLogger.warn).toHaveBeenCalledWith(
      'Companion Error Boundary caught an error',
      expect.objectContaining({
        error: expect.objectContaining({
          name: 'Error',
          message: 'Test error',
          stack: expect.any(String),
        }),
        errorInfo: expect.objectContaining({
          componentStack: expect.any(String),
        }),
        boundary: 'CompanionErrorBoundary',
      })
    );
  });

  it('should hide companion when error occurs but not crash app', () => {
    const { queryByText } = render(
      <CompanionErrorBoundary>
        <ThrowError />
      </CompanionErrorBoundary>
    );

    // Should not render anything (returns null)
    expect(queryByText('Test error')).toBeNull();
  });

  it('should not log when no error occurs', () => {
    render(
      <CompanionErrorBoundary>
        <ThrowError shouldThrow={false} />
      </CompanionErrorBoundary>
    );

    expect(mockedLogger.warn).not.toHaveBeenCalled();
  });
});