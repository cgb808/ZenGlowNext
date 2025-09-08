# Supabase Integration Setup Guide

## Overview

The ZenGlow app now includes a comprehensive Supabase backend integration that provides:

- Real-time parent-child activity monitoring
- Secure authentication and user profiles
- Live meditation session tracking
- Real-time messaging between parent and child devices
- Avatar state synchronization

## Quick Setup

### 1. Install Dependencies

The required packages have already been installed:

```bash
npm install @supabase/supabase-js @react-native-async-storage/async-storage
```

### 2. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your project URL and anon key from Settings > API

### 3. Configure Environment

1. Copy `.env.example` to `.env`
2. Fill in your Supabase credentials:

```
EXPO_PUBLIC_SUPABASE_URL=your_project_url
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

### 4. Setup Database Schema

1. In your Supabase dashboard, go to SQL Editor
2. Copy and paste the contents of `src/database/schema.sql`
3. Run the SQL to create all tables, policies, and functions

### 5. Enable Real-time

1. In Supabase dashboard, go to Database > Replication
2. Enable real-time for these tables:
   - `profiles`
   - `parent_child_connections`
   - `meditation_sessions`
   - `realtime_messages`
   - `avatar_states`

## Architecture

### Database Schema (`src/database/schema.sql`)

- **profiles**: User accounts with parent/child roles
- **parent_child_connections**: Links parent to child accounts
- **meditation_sessions**: Tracks meditation progress
- **realtime_messages**: Parent-child communication
- **avatar_states**: ZenMoon avatar synchronization
- **activity_logs**: Detailed activity tracking
- **session_participants**: Multi-user session support
- **connection_codes**: Secure pairing codes

### Supabase Client (`src/lib/supabase.ts`)

- Configured client with authentication
- Database helpers for type-safe operations
- Real-time subscription management
- Automatic token refresh

### React Hooks (`src/hooks/useSupabase.ts`)

- `useAuth`: Authentication management
- `useProfile`: User profile operations
- `useParentChildConnection`: Connection management
- `useMeditationSession`: Session tracking
- `useRealtimeMessages`: Live messaging
- `useAvatarState`: Avatar synchronization
- `useZenGlowSync`: Complete integration hook

### Components

- **ParentActivityMonitorRN**: Real-time parent dashboard
- **ZenMoonFaceFloating**: Avatar with Supabase state sync

## Usage Examples

### Authentication

```typescript
const { auth, signIn, signOut, signUp } = useAuth();

// Sign up new user
await signUp('email@example.com', 'password', { role: 'parent' });

// Sign in
await signIn('email@example.com', 'password');
```

### Parent-Child Connection

```typescript
const { connection, generateCode, connectWithCode } = useParentChildConnection(userId);

// Parent generates connection code
const code = await generateCode();

// Child connects using code
await connectWithCode(code);
```

### Meditation Session

```typescript
const { session, startSession, updateProgress, endSession } = useMeditationSession(userId);

// Start new session
await startSession('breathing_exercise', 300); // 5 minutes

// Update progress
await updateProgress(0.5); // 50% complete

// End session
await endSession();
```

### Real-time Messaging

```typescript
const { messages, sendMessage } = useRealtimeMessages(connectionId);

// Send message to connected device
await sendMessage('Great job on your meditation!', 'encouragement');
```

## Security Features

### Row Level Security (RLS)

- Users can only access their own data
- Parents can only see connected children's data
- Children can only see their own sessions and parent messages

### Authentication

- Secure JWT token authentication
- Automatic token refresh
- Role-based access control

### Connection Security

- Time-limited connection codes
- Secure pairing process
- Encrypted data transmission

## Real-time Features

### Live Synchronization

- Avatar state updates in real-time
- Meditation progress sync
- Instant messaging
- Connection status updates

### Offline Support

- Data cached locally with AsyncStorage
- Automatic sync when connection restored
- Optimistic updates for better UX

## Troubleshooting

### Common Issues

1. **Environment variables not loading**: Ensure `.env` file is in project root
2. **RLS policy errors**: Check user authentication status
3. **Real-time not working**: Verify real-time is enabled for tables
4. **Type errors**: Ensure database types are up to date

### Debug Tools

- Enable Supabase debug mode in development
- Check browser network tab for API calls
- Use Supabase dashboard for real-time monitoring

## Next Steps

1. Deploy database schema to your Supabase project
2. Configure environment variables
3. Test authentication flow
4. Test parent-child connection
5. Test real-time features
6. Deploy to production
