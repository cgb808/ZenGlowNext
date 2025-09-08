#!/usr/bin/env node
import fs from 'fs';
import path from 'path';

const projectRoot = process.cwd();
const pkgPath = path.join(projectRoot, 'package.json');

function readJSON(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    console.error(`Failed to read ${file}:`, e.message);
    process.exit(1);
  }
}

const pkg = readJSON(pkgPath);
const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };

const groups = {
  core: [
    'react-native',
    'react',
    '@react-navigation/native',
    '@react-navigation/native-stack',
    'react-native-gesture-handler',
    'react-native-safe-area-context',
    'react-native-screens',
    'react-native-reanimated',
  ],
  state_storage: [
    '@react-native-async-storage/async-storage',
    '@react-native-community/datetimepicker',
  ],
  audio_media: ['expo-av'],
  ui_optional: ['react-native-paper', 'native-base'],
  calendar: ['react-native-calendars'],
  charts: ['react-native-chart-kit', 'react-native-svg'],
  dev_metro: ['expo', 'expo-status-bar', 'react-dom', 'react-native-web', 'uuid'],
};

function checkList(title, list) {
  const missing = [];
  const present = [];
  for (const name of list) {
    if (deps[name]) present.push(`${name}@${deps[name]}`);
    else missing.push(name);
  }
  return { title, present, missing };
}

const results = [
  checkList('Core', groups.core),
  checkList('State & Storage (optional)', groups.state_storage),
  checkList('Audio & Media', groups.audio_media),
  checkList('UI (optional)', groups.ui_optional),
  checkList('Calendar (planned)', groups.calendar),
  checkList('Charts', groups.charts),
  checkList('Dev & Metro', groups.dev_metro),
];

const isExpoManaged = Boolean(deps['expo']);

console.log(
  `\nZenGlow dependency audit\n- Project: ${pkg.name || 'unknown'}@${
    pkg.version || '0.0.0'
  }\n- Expo managed: ${isExpoManaged ? 'YES' : 'NO'}\n`,
);

let missingTotal = 0;
for (const r of results) {
  console.log(`## ${r.title}`);
  if (r.present.length) console.log('Present:', r.present.join(', '));
  if (r.missing.length) console.log('Missing:', r.missing.join(', '));
  else console.log('Missing: none');
  console.log('');
  missingTotal += r.missing.length;
}

// Extra sanity checks
const extras = [];
if (!deps['expo-router']) extras.push('expo-router (recommended)');
if (!deps['expo-system-ui']) extras.push('expo-system-ui (SDK 53 recommended)');
if (!deps['expo-linear-gradient']) extras.push('expo-linear-gradient (used in UI)');
if (!deps['expo-av']) extras.push('expo-av (required by ZenSoundProvider)');

if (extras.length) {
  console.log('Recommendations:', extras.join(', '));
}

console.log(`Summary: ${missingTotal} required/optional packages missing in listed groups.`);

// Exit code indicates if anything missing from required groups (Core, Audio, Dev)
const requiredMissing = [results[0], results[2], results[6]].flatMap((r) => r.missing);
process.exit(requiredMissing.length ? 2 : 0);
