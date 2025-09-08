import 'dotenv/config';
import type { ConfigContext, ExpoConfig } from 'expo/config';
// Keep app.json as the source of static config and layer env-driven extras here
// This reads SUPABASE_URL and SUPABASE_ANON_KEY from your shell/.env
// and exposes them to the app via Constants.expoConfig.extra
// (Never put SERVICE_ROLE_KEY into client extras)

 
const appJson = require('./app.json');

export default ({ config }: ConfigContext): ExpoConfig => {
  const base = (appJson?.expo || {}) as ExpoConfig;
  
  // Extract feature flag environment variables
  const featureFlags: Record<string, boolean> = {};
  Object.keys(process.env).forEach(key => {
    if (key.startsWith('FLAG_')) {
      const flagName = key.substring(5); // Remove 'FLAG_' prefix
      featureFlags[flagName] = process.env[key]?.toLowerCase() === 'true';
    }
  });
  
  return {
    ...base,
    extra: {
      ...(base.extra || {}),
      supabaseUrl: process.env.SUPABASE_URL,
      supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
      featureFlags,
    },
  } as ExpoConfig;
};
