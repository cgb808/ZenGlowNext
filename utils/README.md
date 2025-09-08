# Utils Directory

## SecretFetcher

The `secretFetcher.ts` file is responsible for initializing the Supabase client and fetching secrets securely. Ensure the following:

1. **Environment Variables**:

   - `SUPABASE_URL`: The URL of your Supabase project.
   - `SERVICE_ROLE_KEY`: The service role key for your Supabase project.

2. **Usage**:

   - Import the `testSupabaseClient` function and call it to test the Supabase client initialization.

3. **Security**:
   - Never expose the `SERVICE_ROLE_KEY` in client-side code.
   - Use environment variables to store sensitive information.

## CORS Handler

The `corsHandler.js` file dynamically handles CORS headers based on the request's origin. It includes:

1. **Allowed Origins**:

   - Specify trusted domains in the `allowedOrigins` array.

2. **Dynamic Origin Handling**:

   - The `getCorsHeaders` function checks if the request's origin is allowed and sets the appropriate headers.

3. **Integration**:
   - Use the `getCorsHeaders` function in your server middleware to handle CORS.

## Auth Config

The `authConfig.ini` file contains authentication-related settings for Supabase. Key settings include:

1. **Site URL**:

   - The primary URL of your application.

2. **Additional Redirect URLs**:

   - Specify additional URLs allowed for redirects after authentication.

3. **JWT Expiry**:

   - Set the expiration time for JSON Web Tokens (JWT).

4. **Rate Limits**:
   - Define the maximum number of requests allowed per unit of time.

## Best Practices

- Always validate environment variables before starting the server.
- Restrict CORS access to trusted domains in production.
- Regularly review and update authentication settings to ensure security.
