// src/utils/errorHandler.ts
/**
 * Standardized error handler for ZenGlow
 * Logs error and returns a user-friendly message
 * @param err - The error object or value
 * @param defaultMessage - Fallback message if error is not an instance of Error
 * @returns string - Error message for display
 */
export function handleError(err: any, defaultMessage: string): string {
  console.error(defaultMessage, err);
  return err instanceof Error ? err.message : defaultMessage;
}
