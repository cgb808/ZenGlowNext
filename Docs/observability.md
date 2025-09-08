# 🔍 Observability Guide

This document outlines ZenGlow's centralized logging and error handling infrastructure for better observability and debugging.

## Overview

ZenGlow implements a centralized logging abstraction that provides:
- Structured logging with configurable levels
- Environment-aware log adapters
- Global error boundary integration
- React hook for component-level logging

## Architecture

### Core Components

1. **Logger** (`src/lib/logging.ts`) - Main logging interface
2. **Log Adapters** - Environment-specific output handlers
3. **Error Boundaries** - Global error capture and logging
4. **useLogger Hook** - React component integration

## Usage

### Basic Logging

```typescript
import { logger } from '../src/lib/logging';

// Direct logging
logger.info('User logged in', { userId: '123' });
logger.error('API call failed', { endpoint: '/api/users', error: errorDetails });
```

### Component Logging with Hook

```typescript
import { useLogger } from '../hooks/useLogger';

function MyComponent() {
  const log = useLogger('MyComponent');
  
  const handleClick = () => {
    log.info('Button clicked', { buttonId: 'submit' });
  };
  
  return <button onClick={handleClick}>Submit</button>;
}
```

### Log Levels

The system supports four log levels (in order of priority):

1. **debug** - Detailed diagnostic information
2. **info** - General information about app operation
3. **warn** - Warning conditions that don't prevent operation
4. **error** - Error conditions that may affect functionality

## Configuration

### Environment Variables

Set the minimum log level using the `LOG_LEVEL` environment variable:

```bash
# Show only warnings and errors
LOG_LEVEL=warn

# Show all logs (development default)
LOG_LEVEL=debug

# Production default
LOG_LEVEL=info
```

### Adapters

The system automatically selects the appropriate adapter based on environment:

- **Development**: `ConsoleLogAdapter` - logs to browser/development console
- **Production**: `RemoteLogAdapter` - placeholder for remote logging service

## Error Boundaries

ZenGlow includes global error boundaries that automatically capture and log React errors:

### AppErrorBoundary
- Catches application-level errors
- Logs with `error` level
- Shows user-friendly error UI with retry option

### CompanionErrorBoundary
- Catches ZenGlow companion-specific errors
- Logs with `warn` level (non-critical)
- Silently hides companion on error (app continues)

## Log Structure

All log entries follow a consistent structure:

```typescript
{
  level: 'info' | 'debug' | 'warn' | 'error',
  message: string,
  timestamp: Date,
  meta?: {
    component?: string,    // Component name (when using useLogger)
    userId?: string,       // User context
    sessionId?: string,    // Session context
    error?: {              // Error details
      name: string,
      message: string,
      stack: string
    },
    // ... additional context
  }
}
```

## Best Practices

### When to Log

- **debug**: Detailed flow information, variable states
- **info**: User actions, system state changes, successful operations
- **warn**: Recoverable errors, deprecated usage, performance concerns
- **error**: Failures, exceptions, critical issues

### Metadata Guidelines

Always include relevant context:

```typescript
// Good: Includes actionable context
log.error('Failed to save user preferences', {
  userId: user.id,
  preferences: preferences,
  error: error.message,
  retryCount: 3
});

// Poor: Lacks context
log.error('Save failed');
```

### Component Logging

Use the component name parameter for better traceability:

```typescript
// Preferred
const log = useLogger('UserDashboard');

// Alternative with manual metadata
const log = useLogger();
log.info('Dashboard loaded', { component: 'UserDashboard' });
```

## Testing

The logging system includes comprehensive tests:

- **Unit tests**: `__tests__/lib/logging.test.ts`
- **Hook tests**: `__tests__/hooks/useLogger.test.ts`
- **Error boundary tests**: `__tests__/app/errorBoundary.test.ts`

Run tests with:
```bash
npm test -- logging
```

## Monitoring & Alerting

### Development
- All logs appear in development console
- Error boundaries show visual error states
- Failed adapter calls log to console

### Production
- Remote adapter sends logs to external service (TODO: implement)
- Critical errors can trigger alerts
- Log aggregation enables trend analysis

## Future Enhancements

1. **Remote Logging Integration**
   - Implement actual remote logging service
   - Add log buffering and retry logic
   - Support offline logging

2. **Advanced Filtering**
   - Component-specific log levels
   - Dynamic level changes
   - Sampling for high-volume logs

3. **Performance Monitoring**
   - Automatic performance metrics
   - User interaction timing
   - Component render performance

4. **Security Logging**
   - Authentication events
   - Authorization failures
   - Sensitive data access

## Troubleshooting

### Common Issues

**Logs not appearing in development:**
- Check `LOG_LEVEL` environment variable
- Verify console isn't filtered
- Check adapter configuration

**Error boundary not catching errors:**
- Ensure errors occur during render
- Check error boundary placement
- Verify React error boundary lifecycle

**Performance impact:**
- Use appropriate log levels
- Avoid large metadata objects
- Consider async logging for high-volume scenarios

## Related Documentation

- [Security Implementation Guide](./Security_Implementation_Guide.md)
- [Development Setup](./development-snippets.md)
- [Testing Guidelines](../README.md#testing)