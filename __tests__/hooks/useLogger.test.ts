/**
 * Tests for useLogger hook
 */

import React from 'react';
import { renderHook } from '@testing-library/react-native';
import { useLogger } from '../../hooks/useLogger';
import { logger } from '../../src/lib/logging';

// Mock the logger
jest.mock('../../src/lib/logging', () => ({
  logger: {
    log: jest.fn(),
  },
}));

const mockedLogger = logger as jest.Mocked<typeof logger>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('useLogger', () => {
  it('should provide all log level methods', () => {
    const { result } = renderHook(() => useLogger());

    expect(result.current).toHaveProperty('debug');
    expect(result.current).toHaveProperty('info');
    expect(result.current).toHaveProperty('warn');
    expect(result.current).toHaveProperty('error');
    expect(result.current).toHaveProperty('log');
  });

  it('should call logger with correct parameters', () => {
    const { result } = renderHook(() => useLogger());

    result.current.info('test message', { key: 'value' });

    expect(mockedLogger.log).toHaveBeenCalledWith(
      'info',
      'test message',
      { key: 'value' }
    );
  });

  it('should include component name in metadata when provided', () => {
    const { result } = renderHook(() => useLogger('TestComponent'));

    result.current.warn('test warning');

    expect(mockedLogger.log).toHaveBeenCalledWith(
      'warn',
      'test warning',
      { component: 'TestComponent' }
    );
  });

  it('should merge component name with existing metadata', () => {
    const { result } = renderHook(() => useLogger('TestComponent'));

    result.current.error('test error', { userId: '123' });

    expect(mockedLogger.log).toHaveBeenCalledWith(
      'error',
      'test error',
      { userId: '123', component: 'TestComponent' }
    );
  });

  it('should work with generic log method', () => {
    const { result } = renderHook(() => useLogger('TestComponent'));

    result.current.log('debug', 'debug message', { extra: 'data' });

    expect(mockedLogger.log).toHaveBeenCalledWith(
      'debug',
      'debug message',
      { extra: 'data', component: 'TestComponent' }
    );
  });

  it('should handle undefined metadata gracefully', () => {
    const { result } = renderHook(() => useLogger());

    result.current.info('test message');

    expect(mockedLogger.log).toHaveBeenCalledWith(
      'info',
      'test message',
      {}
    );
  });
});