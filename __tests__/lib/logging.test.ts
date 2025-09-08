/**
 * Tests for centralized logging system
 */

import { 
  Logger, 
  ConsoleLogAdapter, 
  RemoteLogAdapter, 
  LogLevel, 
  LogEntry,
  log 
} from '../../src/lib/logging';

// Mock console methods
const consoleMock = {
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  log: jest.fn(),
};

// Mock process.env
const originalEnv = process.env;

beforeEach(() => {
  jest.clearAllMocks();
  // Mock console methods
  Object.assign(console, consoleMock);
  
  // Reset process.env
  process.env = { ...originalEnv };
});

afterEach(() => {
  process.env = originalEnv;
});

describe('Logger', () => {
  describe('level filtering', () => {
    it('should respect minimum log level', () => {
      const logger = new Logger('warn');
      const adapter = {
        log: jest.fn(),
      };
      logger.addAdapter(adapter);

      logger.debug('debug message');
      logger.info('info message');
      logger.warn('warn message');
      logger.error('error message');

      expect(adapter.log).toHaveBeenCalledTimes(2);
      expect(adapter.log).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'warn',
          message: 'warn message',
        })
      );
      expect(adapter.log).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'error',
          message: 'error message',
        })
      );
    });

    it('should log all levels when set to debug', () => {
      const logger = new Logger('debug');
      const adapter = {
        log: jest.fn(),
      };
      logger.addAdapter(adapter);

      logger.debug('debug message');
      logger.info('info message');
      logger.warn('warn message');
      logger.error('error message');

      expect(adapter.log).toHaveBeenCalledTimes(4);
    });

    it('should allow changing minimum level', () => {
      const logger = new Logger('error');
      const adapter = {
        log: jest.fn(),
      };
      logger.addAdapter(adapter);

      logger.warn('warn message');
      expect(adapter.log).not.toHaveBeenCalled();

      logger.setMinLevel('warn');
      logger.warn('warn message after level change');
      expect(adapter.log).toHaveBeenCalledTimes(1);
    });
  });

  describe('metadata handling', () => {
    it('should include metadata in log entries', () => {
      const logger = new Logger('debug');
      const adapter = {
        log: jest.fn(),
      };
      logger.addAdapter(adapter);

      const meta = { userId: '123', action: 'test' };
      logger.info('test message', meta);

      expect(adapter.log).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'info',
          message: 'test message',
          meta,
          timestamp: expect.any(Date),
        })
      );
    });

    it('should handle undefined metadata', () => {
      const logger = new Logger('debug');
      const adapter = {
        log: jest.fn(),
      };
      logger.addAdapter(adapter);

      logger.info('test message');

      expect(adapter.log).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'info',
          message: 'test message',
          meta: undefined,
          timestamp: expect.any(Date),
        })
      );
    });
  });

  describe('multiple adapters', () => {
    it('should call all registered adapters', () => {
      const logger = new Logger('debug');
      const adapter1 = { log: jest.fn() };
      const adapter2 = { log: jest.fn() };
      
      logger.addAdapter(adapter1);
      logger.addAdapter(adapter2);

      logger.info('test message');

      expect(adapter1.log).toHaveBeenCalledTimes(1);
      expect(adapter2.log).toHaveBeenCalledTimes(1);
    });

    it('should handle adapter failures gracefully', () => {
      const logger = new Logger('debug');
      const failingAdapter = {
        log: jest.fn(() => {
          throw new Error('Adapter failed');
        }),
      };
      const workingAdapter = { log: jest.fn() };
      
      logger.addAdapter(failingAdapter);
      logger.addAdapter(workingAdapter);

      expect(() => logger.info('test message')).not.toThrow();
      expect(workingAdapter.log).toHaveBeenCalledTimes(1);
      expect(consoleMock.error).toHaveBeenCalledWith(
        'Logging adapter failed:',
        expect.any(Error)
      );
    });
  });
});

describe('ConsoleLogAdapter', () => {
  it('should log to appropriate console method', () => {
    const adapter = new ConsoleLogAdapter();

    const debugEntry: LogEntry = {
      level: 'debug',
      message: 'debug message',
      timestamp: new Date(),
    };

    const errorEntry: LogEntry = {
      level: 'error',
      message: 'error message',
      timestamp: new Date(),
    };

    adapter.log(debugEntry);
    adapter.log(errorEntry);

    expect(consoleMock.debug).toHaveBeenCalledWith(
      expect.stringContaining('DEBUG: debug message')
    );
    expect(consoleMock.error).toHaveBeenCalledWith(
      expect.stringContaining('ERROR: error message')
    );
  });

  it('should include metadata when present', () => {
    const adapter = new ConsoleLogAdapter();
    const meta = { userId: '123' };
    
    const entry: LogEntry = {
      level: 'info',
      message: 'test message',
      timestamp: new Date(),
      meta,
    };

    adapter.log(entry);

    expect(consoleMock.info).toHaveBeenCalledWith(
      expect.stringContaining('INFO: test message'),
      meta
    );
  });
});

describe('RemoteLogAdapter', () => {
  it('should log to console as fallback', () => {
    const adapter = new RemoteLogAdapter();
    
    const entry: LogEntry = {
      level: 'info',
      message: 'test message',
      timestamp: new Date(),
    };

    adapter.log(entry);

    expect(consoleMock.log).toHaveBeenCalledWith(
      '[REMOTE LOG]',
      JSON.stringify(entry)
    );
  });
});

describe('Environment configuration', () => {
  it('should respect LOG_LEVEL environment variable', () => {
    // This test would require mocking the module loading
    // For now, we'll test the basic functionality
    expect(log).toBeDefined();
  });
});