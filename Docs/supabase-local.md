# Local Supabase Development Stack

This guide covers how to use the local Supabase services included in the ZenGlow docker-compose.yml for development purposes.

## Overview

The local Supabase stack includes all essential services for full-featured development:

- **PostgreSQL Database** (port 54321) - Main database with Supabase extensions
- **GoTrue Auth** (port 9999) - Authentication service
- **PostgREST API** (port 3000) - Auto-generated REST API
- **Realtime** (port 4000) - Real-time subscriptions
- **Storage** (port 5000) - File storage service  
- **Kong Gateway** (port 8000) - API gateway with auth
- **ImgProxy** (port 5001) - Image transformation
- **Inbucket** (port 9000) - Local email testing

## Starting the Services

### Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (see [Environment Variables](#environment-variables))

### Quick Validation

Before starting, you can validate your setup:

```bash
# Run the validation script
./scripts/test-supabase-local.sh
```

This will check that all required files are present and Docker is properly configured.

### Start All Services

```bash
# Start the complete local development stack
docker-compose up -d

# Check service status
docker-compose ps

# View logs for specific service
docker-compose logs supabase-db
docker-compose logs supabase-auth
```

### Start Only Supabase Services

```bash
# Start just the Supabase stack
docker-compose up -d supabase-db supabase-auth supabase-rest supabase-realtime supabase-storage supabase-kong supabase-imgproxy supabase-inbucket
```

## Environment Variables

The local stack uses demo keys that are **safe for development only**. 

### Required Variables (.env file)

Create a `.env` file in the project root. You have two options:

#### Option 1: Local Development (Recommended for development)

```bash
# === LOCAL DEVELOPMENT SETUP ===
# Local Supabase API Gateway URL
SUPABASE_URL=http://localhost:8000

# Demo anon key (safe for client-side)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0

# Demo service role key (server-side only)
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU

# Server port for your Node.js application
PORT=3001
```

#### Option 2: Production Supabase (Use your actual project credentials)

```bash
# === PRODUCTION SETUP ===
# Your actual Supabase project URL
SUPABASE_URL=https://your-project.supabase.co

# Your actual anon key from Supabase dashboard
SUPABASE_ANON_KEY=your-actual-anon-key

# Your actual service role key (keep this secret!)
SERVICE_ROLE_KEY=your-actual-service-role-key

# Server port for your Node.js application
PORT=3001
```

**Important**: If you have an existing `.env` file with production credentials, either:
1. Rename it to `.env.production` for backup
2. Comment out the production values and add the local ones above
3. Use environment-specific configuration

### JWT Secret Configuration

All services use the same JWT secret for token validation:

```
JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long
```

⚠️ **SECURITY WARNING**: The demo JWT secret and keys above are public and **must be changed for any non-local environment**. Generate new secrets using:

```bash
# Generate a new JWT secret (32+ characters)
openssl rand -base64 32

# Or use a secure random string generator
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

## Connection URLs

### Direct Service Access

| Service | URL | Purpose |
|---------|-----|---------|
| Kong API Gateway | http://localhost:8000 | Main entry point |
| PostgreSQL | postgresql://zenglow:examplepassword@localhost:54321/zenglow | Direct DB access |
| GoTrue Auth | http://localhost:9999 | Authentication API |
| PostgREST | http://localhost:3000 | REST API |
| Realtime | ws://localhost:4000 | WebSocket subscriptions |
| Storage | http://localhost:5000 | File storage |
| Inbucket (Email) | http://localhost:9000 | Email testing UI |

### Application Configuration

For your ZenGlow application, use the Kong gateway as the main entry point:

```typescript
// Client-side configuration
const supabaseUrl = 'http://localhost:8000'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'

const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

## Server-Side Usage Example

The ZenGlow application includes secure server utilities that use the service role key:

```javascript
// utils/secureServer.js - Example usage
import { createClient } from '@supabase/supabase-js';

// Server-side client with service role privileges
const supabase = createClient(
  process.env.SUPABASE_URL,           // http://localhost:8000
  process.env.SERVICE_ROLE_KEY,       // Service role key from .env
  {
    global: {
      headers: {
        // Forward user authentication for RLS
        Authorization: req.headers['authorization'] || '',
      },
    },
  }
);

// Example: Secure database operation
const { data, error } = await supabase
  .from('audio_clips')
  .select('*')
  .limit(10);
```

### Key Security Practices

1. **Never expose SERVICE_ROLE_KEY to client-side code**
2. **Always forward user auth tokens for Row Level Security (RLS)**
3. **Use the anon key for client-side operations**
4. **Validate user permissions on server-side operations**

## Database Setup

### Initial Schema Setup

1. Access the PostgreSQL database:
   ```bash
   # Connect to local database
   docker-compose exec supabase-db psql -U zenglow -d zenglow
   ```

2. Run your schema migrations:
   ```sql
   -- Enable Supabase extensions
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   
   -- Your application schema here
   CREATE TABLE IF NOT EXISTS audio_clips (
     id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
     title TEXT NOT NULL,
     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

### Row Level Security (RLS)

Enable RLS for secure multi-tenant access:

```sql
-- Enable RLS on your tables
ALTER TABLE audio_clips ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view their own audio clips" ON audio_clips
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own audio clips" ON audio_clips
  FOR INSERT WITH CHECK (auth.uid() = user_id);
```

## Testing and Development

### Email Testing

The local stack includes Inbucket for email testing:

1. Access the web UI: http://localhost:9000
2. All emails sent by GoTrue will appear here
3. Test user registration, password resets, etc.

### API Testing

```bash
# Test the API gateway
curl http://localhost:8000/rest/v1/audio_clips \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"

# Test authentication
curl http://localhost:8000/auth/v1/signup \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker logs with `docker-compose logs [service-name]`
2. **Connection refused**: Ensure all services are running with `docker-compose ps`
3. **Authentication errors**: Verify JWT secret matches across all services
4. **Database connection issues**: Check PostgreSQL is accessible on port 54321

### Useful Commands

```bash
# Restart specific service
docker-compose restart supabase-auth

# View service logs
docker-compose logs -f supabase-kong

# Stop all services
docker-compose down

# Reset database (WARNING: destroys data)
docker-compose down -v
docker-compose up -d
```

### Health Checks

```bash
# Check database connectivity
docker-compose exec supabase-db pg_isready -U zenglow

# Test Kong gateway
curl -I http://localhost:8000

# Test auth service
curl http://localhost:9999/health
```

## Production Migration

When moving to production with hosted Supabase:

1. **Create a new Supabase project** at https://supabase.com
2. **Update environment variables**:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-production-anon-key
   SERVICE_ROLE_KEY=your-production-service-key
   ```
3. **Migrate your database schema** using Supabase dashboard or migrations
4. **Update CORS settings** in your Supabase project
5. **Configure custom domains** if needed

⚠️ **CRITICAL**: Never use the demo keys from this local setup in production!

## Related Documentation

- [Environment Setup Guide](./ENV_SETUP.md) - General environment configuration
- [Supabase Integration Guide](./supabase-setup.md) - Production Supabase setup
- [Docker Compose Reference](../docker-compose.yml) - Service configuration details

## Support

For issues with the local Supabase stack:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review service logs: `docker-compose logs [service-name]`
3. Verify your `.env` configuration matches the examples
4. Ensure all required ports are available (not used by other services)