/**
 * Child Safety and Security Utilities for ZenGlow
 * Ensures all content and interactions are appropriate and safe for children
 */

/**
 * Content safety validator - checks if content is appropriate for children
 * @param {string} content - Content to validate
 * @param {number} childAge - Age of child (6-12)
 * @returns {Object} Validation result with safe flag and reasons
 */
export function validateContentSafety(content, childAge = 8) {
  const result = {
    isSafe: true,
    reasons: [],
    ageAppropriate: true,
    recommendations: []
  };

  if (!content || typeof content !== 'string') {
    result.isSafe = false;
    result.reasons.push('Invalid content provided');
    return result;
  }

  const lowercaseContent = content.toLowerCase();

  // Unsafe keywords that should never appear in child content
  const unsafeKeywords = [
    'violent', 'violence', 'scary', 'frightening', 'dangerous', 'harmful',
    'inappropriate', 'adult', 'mature', 'explicit', 'graphic',
    'disturbing', 'terrifying', 'nightmare', 'horror', 'blood',
    'weapon', 'gun', 'knife', 'fight', 'battle', 'war',
    'death', 'dying', 'kill', 'hurt', 'pain', 'suffering'
  ];

  // Check for unsafe keywords
  const foundUnsafeKeywords = unsafeKeywords.filter(keyword => 
    lowercaseContent.includes(keyword)
  );

  if (foundUnsafeKeywords.length > 0) {
    result.isSafe = false;
    result.reasons.push(`Contains unsafe keywords: ${foundUnsafeKeywords.join(', ')}`);
  }

  // Positive keywords that are encouraged
  const positiveKeywords = [
    'calm', 'peaceful', 'gentle', 'kind', 'friendly', 'happy',
    'joy', 'love', 'caring', 'safe', 'comfortable', 'relaxing',
    'mindful', 'breathing', 'meditation', 'yoga', 'nature',
    'rainbow', 'sunshine', 'flowers', 'animals', 'garden'
  ];

  const foundPositiveKeywords = positiveKeywords.filter(keyword => 
    lowercaseContent.includes(keyword)
  );

  // Age-specific content validation
  if (childAge < 8) {
    const complexConcepts = ['anxiety', 'stress', 'depression', 'worry', 'fear'];
    const foundComplexConcepts = complexConcepts.filter(concept => 
      lowercaseContent.includes(concept)
    );
    
    if (foundComplexConcepts.length > 0) {
      result.ageAppropriate = false;
      result.recommendations.push('Consider simpler language for younger children');
    }
  }

  // Content length validation
  if (content.length > 500 && childAge < 10) {
    result.recommendations.push('Consider shorter content for better attention span');
  }

  // Reading level validation (simple heuristic)
  const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const avgWordsPerSentence = sentences.reduce((total, sentence) => {
    return total + sentence.trim().split(/\s+/).length;
  }, 0) / sentences.length;

  if (avgWordsPerSentence > 10 && childAge < 10) {
    result.recommendations.push('Consider shorter sentences for younger children');
  }

  // Positive reinforcement
  if (foundPositiveKeywords.length >= 3) {
    result.recommendations.push('Great use of positive, calming language!');
  }

  return result;
}

/**
 * Validates user input for safety and appropriateness
 * @param {string} input - User input to validate
 * @returns {Object} Validation result
 */
export function validateUserInput(input) {
  const result = {
    isValid: true,
    isSafe: true,
    errors: [],
    sanitizedInput: input
  };

  if (!input || typeof input !== 'string') {
    result.isValid = false;
    result.errors.push('Input is required');
    return result;
  }

  // Basic sanitization - remove potentially harmful characters
  const sanitized = input
    .replace(/<script[^>]*>.*?<\/script>/gi, '') // Remove script tags
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+\s*=/gi, '') // Remove event handlers
    .trim();

  result.sanitizedInput = sanitized;

  // Length validation
  if (sanitized.length > 200) {
    result.isValid = false;
    result.errors.push('Input too long (max 200 characters)');
  }

  // Check for inappropriate content
  const contentSafety = validateContentSafety(sanitized);
  if (!contentSafety.isSafe) {
    result.isSafe = false;
    result.errors.push('Input contains inappropriate content');
  }

  return result;
}

/**
 * Encrypts sensitive data for child protection
 * @param {string} data - Data to encrypt
 * @param {string} key - Encryption key
 * @returns {string} Encrypted data (simplified for demo)
 */
export function encryptSensitiveData(data, key) {
  if (!data || !key) {
    throw new Error('Data and key are required for encryption');
  }

  if (typeof data !== 'string' || typeof key !== 'string') {
    throw new Error('Data and key must be strings');
  }

  if (key.length < 16) {
    throw new Error('Encryption key must be at least 16 characters');
  }

  // Simplified encryption for demonstration
  // In production, use proper encryption libraries like crypto-js
  const encrypted = btoa(data + key.substring(0, 8));
  return encrypted;
}

/**
 * Decrypts sensitive data
 * @param {string} encryptedData - Encrypted data
 * @param {string} key - Decryption key
 * @returns {string} Decrypted data
 */
export function decryptSensitiveData(encryptedData, key) {
  if (!encryptedData || !key) {
    throw new Error('Encrypted data and key are required for decryption');
  }

  try {
    const decoded = atob(encryptedData);
    const keyPart = key.substring(0, 8);
    
    if (!decoded.endsWith(keyPart)) {
      throw new Error('Invalid decryption key');
    }

    return decoded.substring(0, decoded.length - keyPart.length);
  } catch (error) {
    throw new Error('Failed to decrypt data: ' + error.message);
  }
}

/**
 * Validates session security for child protection
 * @param {Object} session - Session data
 * @returns {Object} Security validation result
 */
export function validateSessionSecurity(session) {
  const result = {
    isSecure: true,
    warnings: [],
    shouldTerminate: false
  };

  if (!session) {
    result.isSecure = false;
    result.shouldTerminate = true;
    result.warnings.push('No session provided');
    return result;
  }

  // Check session expiry
  if (session.expiresAt && new Date(session.expiresAt) < new Date()) {
    result.isSecure = false;
    result.shouldTerminate = true;
    result.warnings.push('Session has expired');
  }

  // Check maximum session duration (2 hours for child safety)
  const maxSessionDuration = 2 * 60 * 60 * 1000; // 2 hours in milliseconds
  if (session.startedAt) {
    const sessionDuration = Date.now() - new Date(session.startedAt).getTime();
    if (sessionDuration > maxSessionDuration) {
      result.isSecure = false;
      result.shouldTerminate = true;
      result.warnings.push('Session duration exceeded safety limit');
    }
  }

  // Check for required security fields
  const requiredFields = ['userId', 'childId', 'parentId'];
  const missingFields = requiredFields.filter(field => !session[field]);
  
  if (missingFields.length > 0) {
    result.isSecure = false;
    result.warnings.push(`Missing required fields: ${missingFields.join(', ')}`);
  }

  // Check for suspicious activity indicators
  if (session.failedAttempts && session.failedAttempts > 3) {
    result.isSecure = false;
    result.shouldTerminate = true;
    result.warnings.push('Too many failed attempts detected');
  }

  return result;
}

/**
 * Validates parental consent and supervision requirements
 * @param {Object} parentalData - Parental consent and supervision data
 * @returns {Object} Validation result
 */
export function validateParentalConsent(parentalData) {
  const result = {
    hasConsent: false,
    isSupervised: false,
    errors: [],
    requirements: []
  };

  if (!parentalData) {
    result.errors.push('Parental data is required');
    result.requirements.push('Parent must provide consent');
    return result;
  }

  // Check for explicit consent
  if (parentalData.consentGiven === true && parentalData.consentDate) {
    const consentDate = new Date(parentalData.consentDate);
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    
    if (consentDate > thirtyDaysAgo) {
      result.hasConsent = true;
    } else {
      result.errors.push('Parental consent has expired (30 days max)');
      result.requirements.push('Renew parental consent');
    }
  } else {
    result.errors.push('No valid parental consent found');
    result.requirements.push('Obtain parental consent');
  }

  // Check supervision status
  if (parentalData.supervisionRequired) {
    if (parentalData.parentPresent === true) {
      result.isSupervised = true;
    } else {
      result.errors.push('Parental supervision required but parent not present');
      result.requirements.push('Parent must be present during app use');
    }
  } else {
    result.isSupervised = true; // Not required
  }

  return result;
}

/**
 * Emergency safety check - immediately terminates unsafe conditions
 * @param {Object} context - Current app context
 * @returns {Object} Emergency response
 */
export function emergencySafetyCheck(context) {
  const response = {
    emergencyTriggered: false,
    actions: [],
    reason: null
  };

  if (!context) {
    response.emergencyTriggered = true;
    response.reason = 'No context available';
    response.actions.push('TERMINATE_SESSION');
    return response;
  }

  // Check for emergency keywords in any user input
  const emergencyKeywords = ['help', 'emergency', 'danger', 'scared', 'unsafe'];
  if (context.lastUserInput) {
    const inputLower = context.lastUserInput.toLowerCase();
    const foundEmergencyKeywords = emergencyKeywords.filter(keyword => 
      inputLower.includes(keyword)
    );
    
    if (foundEmergencyKeywords.length > 0) {
      response.emergencyTriggered = true;
      response.reason = `Emergency keywords detected: ${foundEmergencyKeywords.join(', ')}`;
      response.actions.push('NOTIFY_PARENT');
      response.actions.push('SHOW_EMERGENCY_CONTACTS');
    }
  }

  // Check session security
  if (context.session) {
    const sessionSecurity = validateSessionSecurity(context.session);
    if (sessionSecurity.shouldTerminate) {
      response.emergencyTriggered = true;
      response.reason = 'Session security compromised';
      response.actions.push('TERMINATE_SESSION');
      response.actions.push('REQUIRE_PARENT_REAUTH');
    }
  }

  // Check parental supervision
  if (context.parentalData) {
    const parentalConsent = validateParentalConsent(context.parentalData);
    if (!parentalConsent.hasConsent || !parentalConsent.isSupervised) {
      response.emergencyTriggered = true;
      response.reason = 'Parental supervision requirements not met';
      response.actions.push('PAUSE_APP');
      response.actions.push('REQUEST_PARENT_PRESENCE');
    }
  }

  return response;
}