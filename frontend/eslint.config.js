const js = require('@eslint/js')
const reactHooks = require('eslint-plugin-react-hooks')
const reactRefresh = require('eslint-plugin-react-refresh')
const tseslint = require('typescript-eslint')

module.exports = tseslint.config(
  {
    ignores: [
      '.expo/**',
      'dist/**',
      'node_modules/**',
      'coverage/**',
      'expo-env.d.ts',
      'eslint.config.js',
      'vitest.config.ts',
      'babel.config.js',
      'metro.config.js',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['scripts/**/*.mjs'],
    languageOptions: {
      globals: {
        Buffer: 'readonly',
        process: 'readonly',
      },
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      globals: {
        __DEV__: 'readonly',
        atob: 'readonly',
        fetch: 'readonly',
        Response: 'readonly',
        RequestInit: 'readonly',
        sessionStorage: 'readonly',
        localStorage: 'readonly',
        window: 'readonly',
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-undef': 'off',
      'react-hooks/refs': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
)
