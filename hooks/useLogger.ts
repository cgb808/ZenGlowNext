/**
 * useLogger Hook
 * 
 * Provides easy access to the centralized logging system for React components
 */

import { useCallback } from 'react';
import { logger, LogLevel, LogMeta } from '../src/lib/logging';

export interface UseLoggerReturn {
  debug: (message: string, meta?: LogMeta) => void;
  info: (message: string, meta?: LogMeta) => void;
  warn: (message: string, meta?: LogMeta) => void;
  error: (message: string, meta?: LogMeta) => void;
  log: (level: LogLevel, message: string, meta?: LogMeta) => void;
}

/**
 * React hook for accessing the centralized logger
 * 
 * @param componentName Optional component name to include in log metadata
 * @returns Logger interface with all log level methods
 */
export function useLogger(componentName?: string): UseLoggerReturn {
  const createLogMethod = useCallback(
    (level: LogLevel) => (message: string, meta?: LogMeta) => {
      const enhancedMeta: LogMeta = {
        ...meta,
        ...(componentName && { component: componentName }),
      };
      
      logger.log(level, message, enhancedMeta);
    },
    [componentName]
  );

  const debug = useCallback(createLogMethod('debug'), [createLogMethod]);
  const info = useCallback(createLogMethod('info'), [createLogMethod]);
  const warn = useCallback(createLogMethod('warn'), [createLogMethod]);
  const error = useCallback(createLogMethod('error'), [createLogMethod]);

  const log = useCallback(
    (level: LogLevel, message: string, meta?: LogMeta) => {
      const enhancedMeta: LogMeta = {
        ...meta,
        ...(componentName && { component: componentName }),
      };
      
      logger.log(level, message, enhancedMeta);
    },
    [componentName]
  );

  return {
    debug,
    info,
    warn,
    error,
    log,
  };
}