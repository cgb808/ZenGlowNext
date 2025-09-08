import Constants from 'expo-constants';

export function getSupabaseClientEnv() {
  const supabaseUrl =
    process.env.SUPABASE_URL || (Constants?.expoConfig as any)?.extra?.supabaseUrl;
  const supabaseAnonKey =
    process.env.SUPABASE_ANON_KEY || (Constants?.expoConfig as any)?.extra?.supabaseAnonKey;
  return { supabaseUrl, supabaseAnonKey } as { supabaseUrl?: string; supabaseAnonKey?: string };
}

/**
 * Get feature flag environment variables
 * Looks for FLAG_* environment variables and expo config
 */
export function getFeatureFlagEnv() {
  const flagVars: Record<string, boolean> = {};
  
  // Get from process.env (for server/build time)
  Object.keys(process.env).forEach(key => {
    if (key.startsWith('FLAG_')) {
      const flagName = key.substring(5); // Remove 'FLAG_' prefix
      flagVars[flagName] = process.env[key]?.toLowerCase() === 'true';
    }
  });
  
  // Get from expo config (for client runtime)
  const extraFlags = (Constants?.expoConfig as any)?.extra?.featureFlags || {};
  Object.assign(flagVars, extraFlags);
  
  return flagVars;
}
