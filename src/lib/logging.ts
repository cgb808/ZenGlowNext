/**
 * Centralized Logging Abstraction for ZenGlow
 * 
 * Provides structured logging with level filtering and multiple adapters
 */

// Type declarations for environment variables
declare global {
  var process: {
    env: {
      LOG_LEVEL?: string;
      NODE_ENV?: string;
    };
  } | undefined;
  var __DEV__: boolean | undefined;
}

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogMeta {
  [key: string]: any;
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: Date;
  meta?: LogMeta;
}

export interface LogAdapter {
  log(entry: LogEntry): void;
}

/**
 * Console adapter for development environment
 */
export class ConsoleLogAdapter implements LogAdapter {
  log(entry: LogEntry): void {
    const timestamp = entry.timestamp.toISOString();
    const logMethod = this.getConsoleMethod(entry.level);
    
    if (entry.meta && Object.keys(entry.meta).length > 0) {
      logMethod(`[${timestamp}] ${entry.level.toUpperCase()}: ${entry.message}`, entry.meta);
    } else {
      logMethod(`[${timestamp}] ${entry.level.toUpperCase()}: ${entry.message}`);
    }
  }

  private getConsoleMethod(level: LogLevel): (...args: any[]) => void {
    switch (level) {
      case 'debug':
        return console.debug;
      case 'info':
        return console.info;
      case 'warn':
        return console.warn;
      case 'error':
        return console.error;
      default:
        return console.log;
    }
  }
}

/**
 * Remote adapter placeholder for production environment
 */
export class RemoteLogAdapter implements LogAdapter {
  log(entry: LogEntry): void {
    // TODO: Implement remote logging to external service
    // For now, fall back to console in production
    console.log('[REMOTE LOG]', JSON.stringify(entry));
  }
}

/**
 * Log level priority mapping for filtering
 */
const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * Centralized Logger class
 */
export class Logger {
  private adapters: LogAdapter[] = [];
  private minLevel: LogLevel;

  constructor(minLevel: LogLevel = 'info') {
    this.minLevel = minLevel;
  }

  addAdapter(adapter: LogAdapter): void {
    this.adapters.push(adapter);
  }

  setMinLevel(level: LogLevel): void {
    this.minLevel = level;
  }

  private shouldLog(level: LogLevel): boolean {
    return LOG_LEVEL_PRIORITY[level] >= LOG_LEVEL_PRIORITY[this.minLevel];
  }

  private createLogEntry(level: LogLevel, message: string, meta?: LogMeta): LogEntry {
    return {
      level,
      message,
      timestamp: new Date(),
      meta,
    };
  }

  debug(message: string, meta?: LogMeta): void {
    this.log('debug', message, meta);
  }

  info(message: string, meta?: LogMeta): void {
    this.log('info', message, meta);
  }

  warn(message: string, meta?: LogMeta): void {
    this.log('warn', message, meta);
  }

  error(message: string, meta?: LogMeta): void {
    this.log('error', message, meta);
  }

  log(level: LogLevel, message: string, meta?: LogMeta): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry = this.createLogEntry(level, message, meta);
    
    this.adapters.forEach(adapter => {
      try {
        adapter.log(entry);
      } catch (error) {
        // Fail silently to prevent logging errors from breaking the app
        console.error('Logging adapter failed:', error);
      }
    });
  }
}

/**
 * Get log level from environment variable with fallback
 */
function getLogLevelFromEnv(): LogLevel {
  // Use global process if available, otherwise default
  const envLevel = (typeof process !== 'undefined' ? process.env.LOG_LEVEL : undefined)?.toLowerCase() as LogLevel;
  const validLevels: LogLevel[] = ['debug', 'info', 'warn', 'error'];
  
  if (envLevel && validLevels.indexOf(envLevel) !== -1) {
    return envLevel;
  }
  
  // Default to 'info' in production, 'debug' in development
  const nodeEnv = typeof process !== 'undefined' ? process.env.NODE_ENV : 'development';
  return nodeEnv === 'production' ? 'info' : 'debug';
}

/**
 * Check if running in development environment
 */
function isDevelopment(): boolean {
  const nodeEnv = typeof process !== 'undefined' ? process.env.NODE_ENV : 'development';
  const devFlag = typeof __DEV__ !== 'undefined' ? __DEV__ : true;
  return nodeEnv === 'development' || devFlag;
}

/**
 * Global logger instance
 */
export const logger = new Logger(getLogLevelFromEnv());

// Add appropriate adapter based on environment
if (isDevelopment()) {
  logger.addAdapter(new ConsoleLogAdapter());
} else {
  logger.addAdapter(new RemoteLogAdapter());
}

/**
 * Convenience function for direct logging
 */
export function log(level: LogLevel, message: string, meta?: LogMeta): void {
  logger.log(level, message, meta);
}