import dotenv from 'dotenv';
import { fetchSecrets } from './secretFetcher.js';

dotenv.config();

(async () => {
  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceRoleKey) {
    console.error(
      'Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in your .env file.',
    );
    return;
  }

  try {
    // This is a secure use case. The script's purpose is hardcoded.
    // It's intended to fetch secrets for the 'cli' in the 'development' env.
    const secrets = await fetchSecrets('cli', 'development', supabaseUrl, serviceRoleKey);
    console.log('Successfully fetched CLI secrets for development:', secrets);
  } catch (error) {
    console.error('Error fetching secrets for CLI:', error.message);
  }
})();
