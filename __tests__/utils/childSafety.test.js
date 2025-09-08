/**
 * Tests for Child Safety and Security Utilities
 */

import {
  validateContentSafety,
  validateUserInput,
  encryptSensitiveData,
  decryptSensitiveData,
  validateSessionSecurity,
  validateParentalConsent,
  emergencySafetyCheck,
} from '../../src/utils/childSafety';

describe('childSafety utilities', () => {
  describe('validateContentSafety', () => {
    it('approves safe, positive content', () => {
      const content = 'Take a deep breath and imagine a peaceful rainbow in the sky';
      const result = validateContentSafety(content, 8);
      
      expect(result.isSafe).toBe(true);
      expect(result.ageAppropriate).toBe(true);
      expect(result.reasons).toHaveLength(0);
    });

    it('rejects content with unsafe keywords', () => {
      const content = 'This scary story involves violence and frightening monsters';
      const result = validateContentSafety(content, 8);
      
      expect(result.isSafe).toBe(false);
      expect(result.reasons.some(reason => reason.includes('unsafe keywords'))).toBe(true);
    });

    it('flags age-inappropriate content for younger children', () => {
      const content = 'Let\'s talk about anxiety and stress management techniques';
      const result = validateContentSafety(content, 6);
      
      expect(result.ageAppropriate).toBe(false);
      expect(result.recommendations.some(rec => rec.includes('simpler language'))).toBe(true);
    });

    it('accepts age-appropriate content for older children', () => {
      const content = 'Let\'s talk about anxiety and stress management techniques';
      const result = validateContentSafety(content, 10);
      
      expect(result.ageAppropriate).toBe(true);
    });

    it('recommends shorter content for younger children', () => {
      const longContent = 'This is a very long piece of content that goes on and on with many words and sentences that might be too much for younger children to process effectively. '.repeat(4); // Increased to ensure > 500 chars
      const result = validateContentSafety(longContent, 8);
      
      expect(result.recommendations.some(rec => rec.includes('shorter content'))).toBe(true);
    });

    it('recommends shorter sentences for complex language', () => {
      const content = 'This is a very long sentence with many complex words and ideas that might be difficult for younger children to understand and process effectively.';
      const result = validateContentSafety(content, 8);
      
      expect(result.recommendations.some(rec => rec.includes('shorter sentences'))).toBe(true);
    });

    it('praises positive language usage', () => {
      const content = 'Feel calm and peaceful as you breathe gently and enjoy the happy rainbow sunshine';
      const result = validateContentSafety(content, 8);
      
      expect(result.recommendations.some(rec => rec.includes('positive, calming language'))).toBe(true);
    });

    it('handles empty or invalid content', () => {
      expect(validateContentSafety('').isSafe).toBe(false);
      expect(validateContentSafety(null).isSafe).toBe(false);
      expect(validateContentSafety(123).isSafe).toBe(false);
    });
  });

  describe('validateUserInput', () => {
    it('validates safe user input', () => {
      const input = 'I feel happy today and enjoyed the breathing exercise';
      const result = validateUserInput(input);
      
      expect(result.isValid).toBe(true);
      expect(result.isSafe).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.sanitizedInput).toBe(input);
    });

    it('sanitizes HTML and script tags', () => {
      const input = 'Hello <script>alert("test")</script> <b>world</b>';
      const result = validateUserInput(input);
      
      expect(result.sanitizedInput).toBe('Hello  world');
      expect(result.sanitizedInput).not.toContain('<script>');
      expect(result.sanitizedInput).not.toContain('<b>');
    });

    it('removes javascript protocols and event handlers', () => {
      const input = 'javascript:alert("test") onclick=evil()';
      const result = validateUserInput(input);
      
      expect(result.sanitizedInput).not.toContain('javascript:');
      expect(result.sanitizedInput).not.toContain('onclick=');
    });

    it('rejects input that is too long', () => {
      const longInput = 'a'.repeat(201);
      const result = validateUserInput(longInput);
      
      expect(result.isValid).toBe(false);
      expect(result.errors.some(error => error.includes('too long'))).toBe(true);
    });

    it('rejects inappropriate content', () => {
      const input = 'This is scary and violent content';
      const result = validateUserInput(input);
      
      expect(result.isSafe).toBe(false);
      expect(result.errors.some(error => error.includes('inappropriate content'))).toBe(true);
    });

    it('handles empty or invalid input', () => {
      expect(validateUserInput('').isValid).toBe(false);
      expect(validateUserInput(null).isValid).toBe(false);
      expect(validateUserInput(123).isValid).toBe(false);
    });
  });

  describe('encryptSensitiveData', () => {
    const testKey = 'test-encryption-key-32-chars';

    it('encrypts data successfully', () => {
      const data = 'sensitive child data';
      const encrypted = encryptSensitiveData(data, testKey);
      
      expect(encrypted).toBeDefined();
      expect(encrypted).not.toBe(data);
      expect(typeof encrypted).toBe('string');
    });

    it('throws error for missing data or key', () => {
      expect(() => encryptSensitiveData('', testKey)).toThrow('Data and key are required');
      expect(() => encryptSensitiveData('data', '')).toThrow('Data and key are required');
      expect(() => encryptSensitiveData(null, testKey)).toThrow('Data and key are required');
    });

    it('throws error for non-string inputs', () => {
      expect(() => encryptSensitiveData(123, testKey)).toThrow('Data and key must be strings');
      expect(() => encryptSensitiveData('data', 123)).toThrow('Data and key must be strings');
    });

    it('throws error for short encryption key', () => {
      expect(() => encryptSensitiveData('data', 'short')).toThrow('at least 16 characters');
    });
  });

  describe('decryptSensitiveData', () => {
    const testKey = 'test-encryption-key-32-chars';

    it('decrypts data successfully', () => {
      const originalData = 'sensitive child data';
      const encrypted = encryptSensitiveData(originalData, testKey);
      const decrypted = decryptSensitiveData(encrypted, testKey);
      
      expect(decrypted).toBe(originalData);
    });

    it('throws error for invalid decryption key', () => {
      const encrypted = encryptSensitiveData('data', testKey);
      const wrongKey = 'wrong-encryption-key-32-chars';
      
      expect(() => decryptSensitiveData(encrypted, wrongKey)).toThrow('Invalid decryption key');
    });

    it('throws error for missing data or key', () => {
      expect(() => decryptSensitiveData('', testKey)).toThrow('Encrypted data and key are required');
      expect(() => decryptSensitiveData('data', '')).toThrow('Encrypted data and key are required');
    });

    it('throws error for invalid encrypted data', () => {
      expect(() => decryptSensitiveData('invalid-data', testKey)).toThrow('Failed to decrypt data');
    });
  });

  describe('validateSessionSecurity', () => {
    const createValidSession = () => ({
      userId: 'user-123',
      childId: 'child-456',
      parentId: 'parent-789',
      startedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
      expiresAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 minutes from now
      failedAttempts: 0,
    });

    it('validates secure session', () => {
      const session = createValidSession();
      const result = validateSessionSecurity(session);
      
      expect(result.isSecure).toBe(true);
      expect(result.shouldTerminate).toBe(false);
      expect(result.warnings).toHaveLength(0);
    });

    it('detects expired session', () => {
      const session = {
        ...createValidSession(),
        expiresAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
      };
      const result = validateSessionSecurity(session);
      
      expect(result.isSecure).toBe(false);
      expect(result.shouldTerminate).toBe(true);
      expect(result.warnings.some(w => w.includes('expired'))).toBe(true);
    });

    it('detects session duration exceeded', () => {
      const session = {
        ...createValidSession(),
        startedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(), // 3 hours ago
      };
      const result = validateSessionSecurity(session);
      
      expect(result.isSecure).toBe(false);
      expect(result.shouldTerminate).toBe(true);
      expect(result.warnings.some(w => w.includes('duration exceeded'))).toBe(true);
    });

    it('detects missing required fields', () => {
      const session = {
        userId: 'user-123',
        // Missing childId and parentId
        startedAt: new Date().toISOString(),
      };
      const result = validateSessionSecurity(session);
      
      expect(result.isSecure).toBe(false);
      expect(result.warnings.some(w => w.includes('Missing required fields'))).toBe(true);
    });

    it('detects too many failed attempts', () => {
      const session = {
        ...createValidSession(),
        failedAttempts: 5,
      };
      const result = validateSessionSecurity(session);
      
      expect(result.isSecure).toBe(false);
      expect(result.shouldTerminate).toBe(true);
      expect(result.warnings.some(w => w.includes('failed attempts'))).toBe(true);
    });

    it('handles missing session', () => {
      const result = validateSessionSecurity(null);
      
      expect(result.isSecure).toBe(false);
      expect(result.shouldTerminate).toBe(true);
      expect(result.warnings.some(w => w.includes('No session'))).toBe(true);
    });
  });

  describe('validateParentalConsent', () => {
    const createValidParentalData = () => ({
      consentGiven: true,
      consentDate: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(), // 10 days ago
      supervisionRequired: true,
      parentPresent: true,
    });

    it('validates proper parental consent', () => {
      const parentalData = createValidParentalData();
      const result = validateParentalConsent(parentalData);
      
      expect(result.hasConsent).toBe(true);
      expect(result.isSupervised).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('detects expired consent', () => {
      const parentalData = {
        ...createValidParentalData(),
        consentDate: new Date(Date.now() - 35 * 24 * 60 * 60 * 1000).toISOString(), // 35 days ago
      };
      const result = validateParentalConsent(parentalData);
      
      expect(result.hasConsent).toBe(false);
      expect(result.errors.some(e => e.includes('expired'))).toBe(true);
      expect(result.requirements.some(r => r.includes('Renew'))).toBe(true);
    });

    it('detects missing consent', () => {
      const parentalData = {
        ...createValidParentalData(),
        consentGiven: false,
      };
      const result = validateParentalConsent(parentalData);
      
      expect(result.hasConsent).toBe(false);
      expect(result.errors.some(e => e.includes('No valid parental consent'))).toBe(true);
    });

    it('detects missing supervision when required', () => {
      const parentalData = {
        ...createValidParentalData(),
        parentPresent: false,
      };
      const result = validateParentalConsent(parentalData);
      
      expect(result.isSupervised).toBe(false);
      expect(result.errors.some(e => e.includes('supervision required'))).toBe(true);
    });

    it('handles supervision not required', () => {
      const parentalData = {
        ...createValidParentalData(),
        supervisionRequired: false,
        parentPresent: false,
      };
      const result = validateParentalConsent(parentalData);
      
      expect(result.isSupervised).toBe(true); // Not required
    });

    it('handles missing parental data', () => {
      const result = validateParentalConsent(null);
      
      expect(result.hasConsent).toBe(false);
      expect(result.isSupervised).toBe(false);
      expect(result.errors.some(e => e.includes('required'))).toBe(true);
    });
  });

  describe('emergencySafetyCheck', () => {
    const createSafeContext = () => ({
      lastUserInput: 'I feel happy today',
      session: {
        userId: 'user-123',
        childId: 'child-456',
        parentId: 'parent-789',
        startedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        expiresAt: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
        failedAttempts: 0,
      },
      parentalData: {
        consentGiven: true,
        consentDate: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
        supervisionRequired: false,
        parentPresent: true,
      },
    });

    it('returns safe response for normal context', () => {
      const context = createSafeContext();
      const response = emergencySafetyCheck(context);
      
      expect(response.emergencyTriggered).toBe(false);
      expect(response.actions).toHaveLength(0);
      expect(response.reason).toBeNull();
    });

    it('triggers emergency for help keywords', () => {
      const context = {
        ...createSafeContext(),
        lastUserInput: 'I need help, I feel scared',
      };
      const response = emergencySafetyCheck(context);
      
      expect(response.emergencyTriggered).toBe(true);
      expect(response.reason).toContain('Emergency keywords detected');
      expect(response.actions).toContain('NOTIFY_PARENT');
      expect(response.actions).toContain('SHOW_EMERGENCY_CONTACTS');
    });

    it('triggers emergency for session security issues', () => {
      const context = {
        ...createSafeContext(),
        session: {
          ...createSafeContext().session,
          expiresAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // expired
        },
      };
      const response = emergencySafetyCheck(context);
      
      expect(response.emergencyTriggered).toBe(true);
      expect(response.reason).toContain('Session security compromised');
      expect(response.actions).toContain('TERMINATE_SESSION');
    });

    it('triggers emergency for parental supervision issues', () => {
      const context = {
        ...createSafeContext(),
        parentalData: {
          consentGiven: false,
          supervisionRequired: true,
          parentPresent: false,
        },
      };
      const response = emergencySafetyCheck(context);
      
      expect(response.emergencyTriggered).toBe(true);
      expect(response.reason).toContain('Parental supervision');
      expect(response.actions).toContain('PAUSE_APP');
    });

    it('handles missing context', () => {
      const response = emergencySafetyCheck(null);
      
      expect(response.emergencyTriggered).toBe(true);
      expect(response.reason).toContain('No context available');
      expect(response.actions).toContain('TERMINATE_SESSION');
    });
  });
});