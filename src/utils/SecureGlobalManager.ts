/**
 * =================================================================================
 * SECURE GLOBAL MANAGER - Token-Based Global State Management
 * =================================================================================
 * Purpose: Replace insecure global variables with secure token-based system
 * Replaces: global.zenPulse and global.zenSound insecure globals
 * Security Features:
 * - Access token system for function execution
 * - Automatic token expiration (30 minutes)
 * - Unauthorized access detection and logging
 * - Emergency cleanup functionality
 * =================================================================================
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import { useCallback, useEffect, useState } from 'react';

// Security Configuration
const SECURE_GLOBALS_CONFIG = {
  TOKEN_EXPIRY: 30 * 60 * 1000, // 30 minutes
  MAX_ACCESS_ATTEMPTS: 5,
  CLEANUP_INTERVAL: 60 * 1000, // 1 minute
  LOG_UNAUTHORIZED_ACCESS: true,
};

// Types for secure global management
interface SecureToken {
  id: string;
  issuedAt: number;
  expiresAt: number;
  permissions: string[];
  userId?: string;
}

interface GlobalFunction {
  id: string;
  function: () => void | Promise<void>;
  tokenId: string;
  registeredAt: number;
}

interface SecurityEvent {
  type: 'token_issued' | 'token_expired' | 'unauthorized_access' | 'function_executed' | 'emergency_cleanup';
  timestamp: number;
  tokenId?: string;
  functionId?: string;
  details?: any;
}

/**
 * Secure Global State Manager
 */
class SecureGlobalStateManager {
  private tokens: Map<string, SecureToken> = new Map();
  private globalFunctions: Map<string, GlobalFunction> = new Map();
  private securityEvents: SecurityEvent[] = [];
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.startCleanupProcess();
  }

  /**
   * Generate secure access token
   */
  generateSecureToken(permissions: string[] = ['zenPulse', 'zenSound'], userId?: string): string {
    const tokenId = `token_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = Date.now();
    
    const token: SecureToken = {
      id: tokenId,
      issuedAt: now,
      expiresAt: now + SECURE_GLOBALS_CONFIG.TOKEN_EXPIRY,
      permissions,
      userId,
    };

    this.tokens.set(tokenId, token);
    
    this.logSecurityEvent('token_issued', {
      tokenId,
      permissions,
      userId,
      expiresIn: SECURE_GLOBALS_CONFIG.TOKEN_EXPIRY,
    });

    console.log('🔑 Secure token generated:', tokenId);
    return tokenId;
  }

  /**
   * Validate access token
   */
  private validateToken(tokenId: string, requiredPermission?: string): boolean {
    const token = this.tokens.get(tokenId);
    
    if (!token) {
      this.logSecurityEvent('unauthorized_access', {
        reason: 'token_not_found',
        tokenId,
        requiredPermission,
      });
      return false;
    }

    if (Date.now() > token.expiresAt) {
      this.tokens.delete(tokenId);
      this.logSecurityEvent('token_expired', {
        tokenId,
        expiredAt: token.expiresAt,
      });
      return false;
    }

    if (requiredPermission && !token.permissions.includes(requiredPermission)) {
      this.logSecurityEvent('unauthorized_access', {
        reason: 'insufficient_permissions',
        tokenId,
        requiredPermission,
        tokenPermissions: token.permissions,
      });
      return false;
    }

    return true;
  }

  /**
   * Securely register global function
   */
  setSecureGlobalFunction(
    functionName: 'zenPulse' | 'zenSound',
    func: () => void | Promise<void>,
    tokenId: string
  ): boolean {
    if (!this.validateToken(tokenId, functionName)) {
      console.warn(`🚫 Unauthorized attempt to set ${functionName}`);
      return false;
    }

    const functionId = `${functionName}_${Date.now()}`;
    
    this.globalFunctions.set(functionName, {
      id: functionId,
      function: func,
      tokenId,
      registeredAt: Date.now(),
    });

    console.log(`✅ ${functionName} registered securely`);
    return true;
  }

  /**
   * Securely execute global function
   */
  async executeSecureGlobalFunction(
    functionName: 'zenPulse' | 'zenSound',
    tokenId?: string
  ): Promise<boolean> {
    const globalFunc = this.globalFunctions.get(functionName);
    
    if (!globalFunc) {
      console.warn(`⚠️ Function ${functionName} not registered`);
      return false;
    }

    // If no token provided, use the function's original token
    const validationTokenId = tokenId || globalFunc.tokenId;
    
    if (!this.validateToken(validationTokenId, functionName)) {
      console.warn(`🚫 Unauthorized attempt to execute ${functionName}`);
      return false;
    }

    try {
      await globalFunc.function();
      
      this.logSecurityEvent('function_executed', {
        functionName,
        functionId: globalFunc.id,
        tokenId: validationTokenId,
      });

      console.log(`🚀 ${functionName} executed successfully`);
      return true;
    } catch (error) {
      console.error(`❌ Error executing ${functionName}:`, error);
      return false;
    }
  }

  /**
   * Remove global function
   */
  removeSecureGlobalFunction(
    functionName: 'zenPulse' | 'zenSound',
    tokenId: string
  ): boolean {
    const globalFunc = this.globalFunctions.get(functionName);
    
    if (!globalFunc) {
      return true; // Already removed
    }

    // Allow removal with original token or any valid token
    if (!this.validateToken(tokenId) && globalFunc.tokenId !== tokenId) {
      console.warn(`🚫 Unauthorized attempt to remove ${functionName}`);
      return false;
    }

    this.globalFunctions.delete(functionName);
    console.log(`🗑️ ${functionName} removed securely`);
    return true;
  }

  /**
   * Revoke access token
   */
  revokeToken(tokenId: string): boolean {
    if (this.tokens.has(tokenId)) {
      this.tokens.delete(tokenId);
      
      // Remove any functions using this token
      for (const [funcName, func] of this.globalFunctions.entries()) {
        if (func.tokenId === tokenId) {
          this.globalFunctions.delete(funcName);
        }
      }

      console.log('🔒 Token revoked:', tokenId);
      return true;
    }
    return false;
  }

  /**
   * Emergency cleanup - revoke all tokens and functions
   */
  emergencyCleanup(reason: string): void {
    console.warn('🚨 Emergency cleanup triggered:', reason);
    
    this.logSecurityEvent('emergency_cleanup', {
      reason,
      tokensRevoked: this.tokens.size,
      functionsRemoved: this.globalFunctions.size,
    });

    this.tokens.clear();
    this.globalFunctions.clear();

    Alert.alert(
      'Security Alert',
      `All secure global access has been revoked: ${reason}`,
      [{ text: 'OK' }]
    );
  }

  /**
   * Get security status
   */
  getSecurityStatus(): {
    activeTokens: number;
    registeredFunctions: string[];
    recentEvents: SecurityEvent[];
  } {
    return {
      activeTokens: this.tokens.size,
      registeredFunctions: Array.from(this.globalFunctions.keys()),
      recentEvents: this.securityEvents.slice(-10),
    };
  }

  /**
   * Log security events
   */
  private logSecurityEvent(
    type: SecurityEvent['type'],
    details?: any
  ): void {
    const event: SecurityEvent = {
      type,
      timestamp: Date.now(),
      details,
    };

    this.securityEvents.push(event);

    // Keep only last 100 events
    if (this.securityEvents.length > 100) {
      this.securityEvents.splice(0, this.securityEvents.length - 100);
    }

    // Store in AsyncStorage for persistence
    this.persistSecurityEvents();

    if (SECURE_GLOBALS_CONFIG.LOG_UNAUTHORIZED_ACCESS || type !== 'unauthorized_access') {
      console.log(`🔍 Security event: ${type}`, details);
    }
  }

  /**
   * Persist security events to storage
   */
  private async persistSecurityEvents(): Promise<void> {
    try {
      await AsyncStorage.setItem(
        'secure_global_events',
        JSON.stringify(this.securityEvents)
      );
    } catch (error) {
      console.error('Failed to persist security events:', error);
    }
  }

  /**
   * Load security events from storage
   */
  private async loadSecurityEvents(): Promise<void> {
    try {
      const events = await AsyncStorage.getItem('secure_global_events');
      if (events) {
        this.securityEvents = JSON.parse(events);
      }
    } catch (error) {
      console.error('Failed to load security events:', error);
    }
  }

  /**
   * Start cleanup process for expired tokens
   */
  private startCleanupProcess(): void {
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpiredTokens();
    }, SECURE_GLOBALS_CONFIG.CLEANUP_INTERVAL);
  }

  /**
   * Cleanup expired tokens and functions
   */
  private cleanupExpiredTokens(): void {
    const now = Date.now();
    let expiredCount = 0;

    // Remove expired tokens
    for (const [tokenId, token] of this.tokens.entries()) {
      if (now > token.expiresAt) {
        this.tokens.delete(tokenId);
        expiredCount++;

        // Remove functions using expired tokens
        for (const [funcName, func] of this.globalFunctions.entries()) {
          if (func.tokenId === tokenId) {
            this.globalFunctions.delete(funcName);
          }
        }
      }
    }

    if (expiredCount > 0) {
      console.log(`🧹 Cleaned up ${expiredCount} expired tokens`);
    }
  }

  /**
   * Shutdown cleanup process
   */
  shutdown(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }
}

// Singleton instance
const secureGlobalManager = new SecureGlobalStateManager();

/**
 * React Hook for Secure Global Management
 */
export function useSecureGlobals(userId?: string) {
  const [tokenId, setTokenId] = useState<string | null>(null);

  // Generate token on mount
  useEffect(() => {
    const token = secureGlobalManager.generateSecureToken(['zenPulse', 'zenSound'], userId);
    setTokenId(token);

    return () => {
      // Revoke token on unmount
      if (token) {
        secureGlobalManager.revokeToken(token);
      }
    };
  }, [userId]);

  const setZenPulse = useCallback(
    (func: (() => void) | null) => {
      if (!tokenId) return false;

      if (func === null) {
        return secureGlobalManager.removeSecureGlobalFunction('zenPulse', tokenId);
      } else {
        return secureGlobalManager.setSecureGlobalFunction('zenPulse', func, tokenId);
      }
    },
    [tokenId]
  );

  const setZenSound = useCallback(
    (func: (() => Promise<void>) | null) => {
      if (!tokenId) return false;

      if (func === null) {
        return secureGlobalManager.removeSecureGlobalFunction('zenSound', tokenId);
      } else {
        return secureGlobalManager.setSecureGlobalFunction('zenSound', func, tokenId);
      }
    },
    [tokenId]
  );

  const executeZenPulse = useCallback(async () => {
    if (!tokenId) return false;
    return secureGlobalManager.executeSecureGlobalFunction('zenPulse', tokenId);
  }, [tokenId]);

  const executeZenSound = useCallback(async () => {
    if (!tokenId) return false;
    return secureGlobalManager.executeSecureGlobalFunction('zenSound', tokenId);
  }, [tokenId]);

  const getSecurityStatus = useCallback(() => {
    return secureGlobalManager.getSecurityStatus();
  }, []);

  return {
    // Secure setters
    setZenPulse,
    setZenSound,
    
    // Secure executors
    executeZenPulse,
    executeZenSound,
    
    // Utility functions
    getSecurityStatus,
    isTokenValid: tokenId !== null,
    tokenId,
  };
}

// Export manager for advanced usage
export { secureGlobalManager };

// Export legacy-style interface for gradual migration
export const SecureGlobals = {
  /**
   * @deprecated Use useSecureGlobals hook instead
   */
  setZenPulse: (func: (() => void) | null) => {
    console.warn('SecureGlobals.setZenPulse is deprecated. Use useSecureGlobals hook instead.');
    const token = secureGlobalManager.generateSecureToken(['zenPulse']);
    if (func === null) {
      return secureGlobalManager.removeSecureGlobalFunction('zenPulse', token);
    }
    return secureGlobalManager.setSecureGlobalFunction('zenPulse', func, token);
  },
  
  /**
   * @deprecated Use useSecureGlobals hook instead
   */
  executeZenPulse: async () => {
    console.warn('SecureGlobals.executeZenPulse is deprecated. Use useSecureGlobals hook instead.');
    const token = secureGlobalManager.generateSecureToken(['zenPulse']);
    return secureGlobalManager.executeSecureGlobalFunction('zenPulse', token);
  },
};