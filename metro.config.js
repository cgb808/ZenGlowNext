const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Add support for additional asset types
config.resolver.assetExts.push(
  // Audio formats
  'mp3',
  'wav',
  'aac',
  'm4a',
  // Image formats  
  'png',
  'jpg',
  'jpeg',
  'gif',
  'webp',
  'svg'
);

// Add support for .env files
config.resolver.platforms = [...config.resolver.platforms, 'native', 'android', 'ios'];

module.exports = config;
