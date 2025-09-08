import { createClient } from '@supabase/supabase-js';
import getCorsHeaders from './corsHandler';

/**
 * Simplified function to test TypeScript compilation and Supabase client initialization.
 * Replace 'https://example.supabase.co' and 'example-key' with your Supabase URL and anon/public key.
 */
export function testSupabaseClient(req: Request) {
  const origin = req.headers.get('Origin') || '';
  const corsHeaders = getCorsHeaders(origin);

  const supabase = createClient('https://example.supabase.co', 'example-key');
  console.log('Supabase client initialized:', supabase);

  return new Response('Supabase client initialized', {
    headers: corsHeaders,
  });
}
