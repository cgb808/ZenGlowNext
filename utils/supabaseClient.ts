import { createClient } from '@supabase/supabase-js';
import getCorsHeaders from './corsHandler';

/**
 * Secure Supabase client initialization using environment variables.
 * No hardcoded secrets - all values are injected by Docker Compose from .env file.
 */
export function createSecureSupabaseClient(authToken?: string) {
  // Read from environment variables (injected by Docker Compose)
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseServiceRoleKey = process.env.SERVICE_ROLE_KEY;

  if (!supabaseUrl || !supabaseServiceRoleKey) {
    throw new Error('Missing required environment variables: SUPABASE_URL or SERVICE_ROLE_KEY');
  }

  console.log('Initializing Supabase client with URL:', supabaseUrl);

  // Create client with optional auth context
  const clientOptions: {
    global?: {
      headers: {
        Authorization: string;
      };
    };
  } = {};

  if (authToken) {
    clientOptions.global = {
      headers: {
        Authorization: authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`,
      },
    };
    console.log('Supabase client created with auth context');
  }

  return createClient(supabaseUrl, supabaseServiceRoleKey, clientOptions);
}

/**
 * Get authenticated user from JWT token
 */
export async function getAuthenticatedUser(authToken: string) {
  const supabase = createSecureSupabaseClient(authToken);

  try {
    const token = authToken.replace('Bearer ', '');
    const { data, error } = await supabase.auth.getUser(token);

    if (error) {
      throw new Error(`Authentication failed: ${error.message}`);
    }

    return data.user;
  } catch (error) {
    console.error('Failed to get authenticated user:', error);
    throw error;
  }
}

/**
 * Test function to verify Supabase client initialization and CORS handling.
 */
export async function testSupabaseClient(req: Request) {
  const origin = req.headers.get('Origin') || '';
  const corsHeaders = getCorsHeaders(origin);

  try {
    const supabase = createSecureSupabaseClient();
    console.log('✅ Supabase client initialized successfully');

    // Test the connection
    const { data, error } = await supabase.from('audio_clips').select('count').limit(1);
    if (error) {
      console.error('❌ Database connection test failed:', error);
      throw error;
    }
    console.log(
      '✅ Database connection test successful',
      data ? `(${data.length} records found)` : '',
    );

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Supabase client initialized successfully',
        url: process.env.SUPABASE_URL,
        timestamp: new Date().toISOString(),
        testResult: data,
      }),
      {
        status: 200,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      },
    );
  } catch (error) {
    console.error('❌ Failed to initialize Supabase client:', error);

    return new Response(
      JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      }),
      {
        status: 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      },
    );
  }
}
