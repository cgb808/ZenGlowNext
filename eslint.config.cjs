const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');
const globals = require('globals');
const tseslint = require('typescript-eslint');
const jsoncPlugin = require('eslint-plugin-jsonc');
const prettierConfig = require('eslint-config-prettier');
const eslint = require('@eslint/js');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: [
      'dist/*',
      'package-lock.json',
      'utils/dist/*',
      'utils/node_modules/*',
      'eslint.config.cjs',
    ],
  },
  // Base ESLint recommended rules
  eslint.configs.recommended,

  // TypeScript ESLint recommended rules
  ...tseslint.configs.recommended.map((config) => ({
    ...config,
    files: config.files || ['**/*.{ts,tsx}'],
    ignores: [...(config.ignores || []), 'eslint.config.cjs'],
  })),

  // JSON plugin recommended rules
  {
    files: ['**/*.json', '**/*.jsonc', '**/*.json5'],
    languageOptions: {
      parser: require('jsonc-eslint-parser'),
    },
    plugins: {
      jsonc: jsoncPlugin,
    },
    rules: {
      ...jsoncPlugin.configs['recommended-with-jsonc'].rules,
    },
  },

  // Configuration for TypeScript files (React Native/Expo)
  {
    files: ['**/*.{ts,tsx}'],
    ignores: ['utils/**/*'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: './tsconfig.json',
        ecmaVersion: 2022,
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    rules: {
      // Add any specific rules for React Native/Expo files
    },
  },

  // Special configuration for utils directory TypeScript files
  {
    files: ['utils/**/*.ts'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: './utils/tsconfig.json',
        ecmaVersion: 2022,
        sourceType: 'module',
      },
      globals: {
        ...globals.node,
        ...globals.es2022,
      },
    },
    rules: {
      // Disable problematic rules for server code
      'no-unused-expressions': 'off',
      '@typescript-eslint/no-unused-expressions': 'off',
      // Allow console.log in server code
      'no-console': 'off',
    },
  },

  // Special configuration for utils directory JavaScript files
  {
    files: ['utils/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.node,
        ...globals.es2022,
      },
    },
    rules: {
      // Disable problematic rules for server code
      'no-unused-expressions': 'off',
      // Allow console.log in server code
      'no-console': 'off',
    },
  },

  // Configuration for JavaScript/JSX files
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Add any specific rules for JavaScript/JSX files
    },
  },

  // Prettier must be the last configuration to ensure it overrides other formatting rules
  prettierConfig,
]);
