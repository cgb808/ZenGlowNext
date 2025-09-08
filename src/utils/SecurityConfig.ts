/**
 * =================================================================================
 * SECURITY CONFIGURATION - ZenGlow Application Security Settings
 * =================================================================================
 * Purpose: Central configuration for all security features
 * Environment: Production and Development settings
 * =================================================================================
 */

// Environment detection
const IS_PRODUCTION = process.env.NODE_ENV === 'production';
const IS_DEVELOPMENT = process.env.NODE_ENV === 'development';

/**
 * Core Security Configuration
 */
export const SECURITY_CONFIG = {
  // Encryption Settings
  ENCRYPTION: {
    ENABLE_ENCRYPTION: true,
    ALGORITHM: 'AES-256-GCM', // Target algorithm (placeholder implementation currently)
    KEY_LENGTH: 32,
    IV_LENGTH: 16,
    USE_NATIVE_CRYPTO: IS_PRODUCTION, // Use native crypto in production
  },

  // Session Management
  SESSION: {
    TIMEOUT_MS: 30 * 60 * 1000, // 30 minutes
    MAX_FAILED_ATTEMPTS: 3,
    RATE_LIMIT_COOLDOWN_MS: 5 * 1000, // 5 seconds
    HEARTBEAT_INTERVAL_MS: 5 * 60 * 1000, // 5 minutes
    AUTO_CLEANUP_INTERVAL_MS: 60 * 1000, // 1 minute
  },

  // Connection Codes
  CONNECTION_CODES: {
    LENGTH: 12,
    EXPIRY_MS: 60 * 60 * 1000, // 1 hour
    CHARSET: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    MAX_ACTIVE_CODES_PER_PARENT: 3,
  },

  // Global State Security
  GLOBAL_STATE: {
    TOKEN_EXPIRY_MS: 30 * 60 * 1000, // 30 minutes
    MAX_ACCESS_ATTEMPTS: 5,
    PERMISSIONS: ['zenPulse', 'zenSound', 'avatarControl', 'sessionManagement'],
    LOG_UNAUTHORIZED_ACCESS: true,
    AUTO_REVOKE_ON_SUSPICIOUS_ACTIVITY: true,
  },

  // Data Storage
  STORAGE: {
    ENABLE_ENCRYPTION: true,
    DEFAULT_EXPIRY_MS: 7 * 24 * 60 * 60 * 1000, // 7 days
    CLEANUP_INTERVAL_MS: 24 * 60 * 60 * 1000, // 24 hours
    INTEGRITY_CHECK: true,
    MAX_STORAGE_SIZE_MB: 50,
  },

  // Child Data Privacy
  CHILD_PRIVACY: {
    EXCLUDE_SENSITIVE_DATA: true,
    SENSITIVE_FIELDS: ['heartRate', 'stressLevel', 'detailedEmotions', 'privateNotes'],
    DATA_RETENTION_DAYS: 30,
    ANONYMIZE_AFTER_DAYS: 90,
    REQUIRE_PARENT_CONSENT: true,
  },

  // Security Monitoring
  MONITORING: {
    LOG_SECURITY_EVENTS: true,
    MAX_SECURITY_EVENTS: 100,
    ALERT_ON_CRITICAL_EVENTS: true,
    CRITICAL_EVENTS: [
      'emergency_disconnect',
      'encryption_failure',
      'unauthorized_access',
      'data_breach_attempt',
      'session_hijack_attempt',
    ],
  },

  // Development Settings (ignored in production)
  DEVELOPMENT: {
    ENABLE_DEBUG_LOGS: IS_DEVELOPMENT,
    SKIP_ENCRYPTION: false, // Never skip in production
    MOCK_CRYPTO_FUNCTIONS: false,
    EXTENDED_SESSION_TIMEOUT: IS_DEVELOPMENT,
    SHOW_SECURITY_INDICATORS: IS_DEVELOPMENT,
  },

  // Production Security Hardening
  PRODUCTION: {
    ENFORCE_HTTPS: true,
    ENABLE_CERTIFICATE_PINNING: true,
    REQUIRE_BIOMETRIC_AUTH: false, // Future enhancement
    IMPLEMENT_RATE_LIMITING: true,
    USE_HARDWARE_SECURITY_MODULE: false, // Future enhancement
    ENABLE_AUDIT_LOGGING: true,
  },
};

/**
 * Security Event Types
 */
export const SECURITY_EVENTS = {
  // Authentication
  LOGIN_SUCCESS: 'login_success',
  LOGIN_FAILURE: 'login_failure',
  TOKEN_ISSUED: 'token_issued',
  TOKEN_EXPIRED: 'token_expired',
  TOKEN_REVOKED: 'token_revoked',

  // Connection Management
  CONNECTION_ATTEMPT: 'connection_attempt',
  CONNECTION_SUCCESS: 'connection_success',
  CONNECTION_FAILURE: 'connection_failure',
  CONNECTION_TIMEOUT: 'connection_timeout',
  EMERGENCY_DISCONNECT: 'emergency_disconnect',

  // Data Operations
  DATA_ENCRYPTION: 'data_encryption',
  DATA_DECRYPTION: 'data_decryption',
  ENCRYPTION_FAILURE: 'encryption_failure',
  DECRYPTION_FAILURE: 'decryption_failure',
  DATA_SANITIZATION: 'data_sanitization',

  // Security Violations
  UNAUTHORIZED_ACCESS: 'unauthorized_access',
  RATE_LIMIT_EXCEEDED: 'rate_limit_exceeded',
  SUSPICIOUS_ACTIVITY: 'suspicious_activity',
  DATA_BREACH_ATTEMPT: 'data_breach_attempt',
  INJECTION_ATTEMPT: 'injection_attempt',

  // System Events
  SECURITY_INIT: 'security_init',
  SECURITY_SHUTDOWN: 'security_shutdown',
  CLEANUP_EXECUTED: 'cleanup_executed',
  BACKUP_CREATED: 'backup_created',
} as const;

/**
 * Security Permissions
 */
export const SECURITY_PERMISSIONS = {
  // Global Function Access
  ZEN_PULSE: 'zenPulse',
  ZEN_SOUND: 'zenSound',
  AVATAR_CONTROL: 'avatarControl',
  
  // Session Management
  SESSION_CREATE: 'sessionCreate',
  SESSION_MANAGE: 'sessionManage',
  SESSION_MONITOR: 'sessionMonitor',

  // Data Access
  CHILD_DATA_READ: 'childDataRead',
  CHILD_DATA_WRITE: 'childDataWrite',
  PARENT_DATA_READ: 'parentDataRead',
  PARENT_DATA_WRITE: 'parentDataWrite',

  // Administrative
  SECURITY_ADMIN: 'securityAdmin',
  CONNECTION_ADMIN: 'connectionAdmin',
  DATA_ADMIN: 'dataAdmin',
} as const;

/**
 * Get environment-specific security configuration
 */
export function getSecurityConfig() {
  const config = { ...SECURITY_CONFIG };

  // Apply production hardening
  if (IS_PRODUCTION) {
    config.ENCRYPTION.ENABLE_ENCRYPTION = true;
    config.ENCRYPTION.USE_NATIVE_CRYPTO = true;
    config.MONITORING.LOG_SECURITY_EVENTS = true;
    config.STORAGE.ENABLE_ENCRYPTION = true;
    config.DEVELOPMENT.ENABLE_DEBUG_LOGS = false;
  }

  // Apply development settings
  if (IS_DEVELOPMENT) {
    if (config.DEVELOPMENT.EXTENDED_SESSION_TIMEOUT) {
      config.SESSION.TIMEOUT_MS = 60 * 60 * 1000; // 1 hour in dev
    }
  }

  return config;
}

/**
 * Validate security configuration
 */
export function validateSecurityConfig(): boolean {
  const config = getSecurityConfig();
  
  // Critical validations
  if (IS_PRODUCTION) {
    if (!config.ENCRYPTION.ENABLE_ENCRYPTION) {
      console.error('❌ CRITICAL: Encryption must be enabled in production');
      return false;
    }
    
    if (!config.STORAGE.ENABLE_ENCRYPTION) {
      console.error('❌ CRITICAL: Storage encryption must be enabled in production');
      return false;
    }
    
    if (config.SESSION.TIMEOUT_MS > 60 * 60 * 1000) {
      console.error('❌ CRITICAL: Session timeout too long for production');
      return false;
    }
  }

  console.log('✅ Security configuration validated');
  return true;
}

/**
 * Security feature flags
 */
export const SECURITY_FEATURES = {
  ENCRYPTED_COMMUNICATION: true,
  SECURE_GLOBAL_MANAGEMENT: true,
  SECURE_DATA_STORAGE: true,
  SESSION_MANAGEMENT: true,
  RATE_LIMITING: true,
  DATA_SANITIZATION: true,
  SECURITY_MONITORING: true,
  EMERGENCY_DISCONNECT: true,
} as const;

/**
 * Check if a security feature is enabled
 */
export function isSecurityFeatureEnabled(feature: keyof typeof SECURITY_FEATURES): boolean {
  return SECURITY_FEATURES[feature] && validateSecurityConfig();
}

/**
 * Application feature flags
 */
export const APP_FEATURES = {
  RECOMMENDATIONS_ENABLED: process.env.EXPO_PUBLIC_RECOMMENDATIONS_ENABLED === 'true' || process.env.RECOMMENDATIONS_ENABLED === 'true' || false,
} as const;

/**
 * Check if an application feature is enabled
 */
export function isRecommendationsEnabled(): boolean {
  return APP_FEATURES.RECOMMENDATIONS_ENABLED;
}

// Initialize security configuration
if (typeof window !== 'undefined' || typeof global !== 'undefined') {
  // Only validate in runtime environments
  setTimeout(() => {
    if (!validateSecurityConfig()) {
      console.error('🚨 SECURITY CONFIGURATION VALIDATION FAILED');
    }
  }, 0);
}