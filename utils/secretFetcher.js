import fetch from 'node-fetch';

/**
 * Fetch secrets from Supabase Edge Function via HTTP.
 * @param {string} service - The service name (e.g., 'api').
 * @param {string} environment - The environment (e.g., 'production').
 * @param {string} supabaseUrl - Your Supabase project URL (e.g., https://xyz.supabase.co).
 * @param {string} serviceRoleKey - Your Supabase service role key.
 * @returns {Promise<Object>} - The secrets object.
 */
export async function fetchSecrets(service, environment, supabaseUrl, serviceRoleKey) {
  // Edge Function endpoint (update path if needed)
  const edgeFunctionUrl = `${supabaseUrl}/functions/v1/fetch-secrets`;

  const response = await fetch(edgeFunctionUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${serviceRoleKey}`,
    },
    body: JSON.stringify({ service, environment }),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch secrets: ${response.status} ${await response.text()}`);
  }

  const result = await response.json();
  if (result.error) {
    throw new Error(`Edge Function error: ${result.error}`);
  }

  // Edge Function returns { secrets: { ... } }
  return result.secrets || {};
}
