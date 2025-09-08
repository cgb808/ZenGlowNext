"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.testSupabaseClient = testSupabaseClient;
let supabase_js_1 = require("@supabase/supabase-js");
let corsHandler_1 = require("./corsHandler");
/**
 * Simplified function to test TypeScript compilation and Supabase client initialization.
 * Replace 'https://example.supabase.co' and 'example-key' with your Supabase URL and anon/public key.
 */
function testSupabaseClient(req) {
    let origin = req.headers.get('Origin') || '';
    let corsHeaders = (0, corsHandler_1.default)(origin);
    let supabase = (0, supabase_js_1.createClient)('https://example.supabase.co', 'example-key');
    console.log('Supabase client initialized:', supabase);
    return new Response('Supabase client initialized', {
        headers: corsHeaders,
    });
}
