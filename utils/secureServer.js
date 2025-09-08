import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import getCorsHeaders from './corsHandler.js';
import { fetchSecrets } from './secretFetcher.js';

// Load environment variables from .env file
dotenv.config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

// Middleware to check Supabase authentication
const authenticateRequest = async (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1]; // Extract Bearer token
  if (!token) {
    return res.status(401).json({ error: 'Unauthorized: No token provided' });
  }

  const { data: user, error } = await supabase.auth.getUser(token);
  if (error || !user) {
    return res.status(401).json({ error: 'Unauthorized: Invalid token' });
  }

  req.user = user; // Attach user to request object
  next();
};

// Middleware to handle CORS
app.use((req, res, next) => {
  const origin = req.headers.origin;
  const corsHeaders = getCorsHeaders(origin);
  res.set(corsHeaders);

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    return res.status(204).end();
  }

  next();
});

// --- Secure Endpoint ---
// This endpoint is designed for a specific purpose. The service and environment
// are hardcoded on the server. The client cannot request secrets for other services.
app.post('/get-api-keys', authenticateRequest, async (req, res) => {
  // SECURE: The service and environment are defined on the server, not by the client.
  // This endpoint is specifically for the 'api' in the 'production' environment.
  const service = 'api';
  const environment = 'production';

  // You could add authentication/authorization here. For example, check if the
  // user making the request is authorized to get these specific keys.
  // For example: if (!isUserAuthorized(req.user)) { return res.status(403).send('Forbidden'); }

  if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
    console.error('Supabase URL or Service Role Key is not configured.');
    return res.status(500).json({ error: 'Server configuration error.' });
  }

  try {
    console.log(`Fetching secrets for a predefined service: ${service}, env: ${environment}`);
    const secrets = await fetchSecrets(service, environment, SUPABASE_URL, SERVICE_ROLE_KEY);

    // You might not want to return all secrets.
    // For example, just return the specific key the client application needs.
    const specificKey = secrets.STRIPE_PUBLIC_KEY;
    if (!specificKey) {
      return res.status(404).json({ error: 'Required key not found in vault.' });
    }

    res.json({ stripePublicKey: specificKey });
  } catch (error) {
    console.error('Error fetching secrets:', error.message);
    res.status(500).json({ error: 'Failed to retrieve application keys.' });
  }
});

// Example of a secure endpoint
app.get('/secure-data', authenticateRequest, (req, res) => {
  res.json({ message: 'This is secure data', user: req.user });
});

// Test route to log and return environment variables
app.get('/test-env', (req, res) => {
  console.log('Environment Variables:', {
    SUPABASE_URL,
    SERVICE_ROLE_KEY,
    PORT,
  });

  res.json({
    SUPABASE_URL,
    SERVICE_ROLE_KEY,
    PORT,
  });
});

// Add middleware to parse JSON bodies, which your function needs

// --- YOUR CUSTOM FUNCTION LOGIC ---
// This is your Deno function, translated to Node.js/Express.
// We'll expose it at a path similar to the Supabase platform.
app.post('/functions/v1/match-audio-clips', async (req, res) => {
  console.log('Received request for /functions/v1/match-audio-clips');
  try {
    // 1. Get input from the request body
    const { query_embedding, match_threshold = 0.5, match_count = 10 } = req.body;

    // 2. Validate the input
    if (!query_embedding || !Array.isArray(query_embedding)) {
      return res.status(400).json({
        error: 'Missing or invalid query_embedding',
        expected: 'Array of numbers with 384 dimensions',
      });
    }

    // 3. Create a Supabase client
    // It uses environment variables from your docker-compose file.
    // It forwards the user's authentication token for row-level security.
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SERVICE_ROLE_KEY, // Use the SERVICE_ROLE_KEY for server-side calls
      {
        global: {
          headers: {
            // Forward the original Authorization header from the client
            Authorization: req.headers['authorization'] || '',
          },
        },
      },
    );

    // 4. Call your database function via RPC
    const { data, error } = await supabase.rpc('match_audio_clips', {
      query_embedding,
      match_threshold,
      match_count,
    });

    if (error) {
      console.error('Database RPC error:', error.message);
      return res.status(500).json({
        error: 'Database search failed',
        details: error.message,
      });
    }

    // 5. Return the successful result
    return res.status(200).json({
      results: data,
      count: data ? data.length : 0,
    });
  } catch (unexpectedError) {
    console.error('Unexpected server error:', unexpectedError.message);
    return res.status(500).json({
      error: 'Unexpected server error',
      details: unexpectedError.message,
    });
  }
});
// --- END CUSTOM FUNCTION LOGIC ---

// --- SUPABASE PROXY LOGIC ---
// This part stays the same. It forwards all other Supabase traffic.
const options = {
  api: { target: 'http://postgrest:3000', changeOrigin: true },
  auth: { target: 'http://gotrue:9999', changeOrigin: true },
  storage: { target: 'http://storage:5000', changeOrigin: true },
  realtime: { target: 'ws://realtime:4000', ws: true, changeOrigin: true },
};

console.log('Setting up Supabase proxy routes...');
app.use('/rest/v1', createProxyMiddleware(options.api));
app.use('/auth/v1', createProxyMiddleware(options.auth));
app.use('/storage/v1', createProxyMiddleware(options.storage));
app.use('/realtime/v1', createProxyMiddleware(options.realtime));
// --- END PROXY LOGIC ---

app.listen(PORT, () => {
  console.log(`Secure server, proxy, and custom functions running on http://localhost:${PORT}`);
});
