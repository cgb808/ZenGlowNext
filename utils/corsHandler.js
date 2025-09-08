const allowedOrigins = [
  'http://localhost:3000',
  'https://app.zenglow.io',
  'zenglow://',
];

const corsHeaders = {
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  'Content-Type': 'application/json',
};

function getCorsHeaders(origin) {
  const isAllowedOrigin = allowedOrigins.includes(origin);
  return {
    ...corsHeaders,
    'Access-Control-Allow-Origin': isAllowedOrigin ? origin : allowedOrigins[0],
  };
}

export default getCorsHeaders;
