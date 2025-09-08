-- ZenGlow Supabase Database Schema
-- Complete schema for parent-child meditation app with real-time features

-- Enable necessary extensions
create extension if not exists "uuid-ossp";

-- Custom types
create type user_type as enum ('parent', 'child');
create type message_type as enum ('encouragement', 'alert', 'guidance', 'system');
create type activity_type as enum ('meditation', 'exercise', 'screen_time', 'mood_entry');

-- Profiles table (extends auth.users)
create table public.profiles (
  id uuid references auth.users(id) on delete cascade primary key,
  email text not null,
  full_name text,
  avatar_url text,
  user_type user_type not null,
  age integer,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- Parent profiles with specific settings
create table public.parent_profiles (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  receive_progress_notifications boolean default true,
  receive_mood_alerts boolean default true,
  allow_emergency_contact boolean default true,
  notification_schedule jsonb default '{"quiet_hours": {"start": "21:00", "end": "07:00"}, "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}'::jsonb,
  dashboard_preferences jsonb default '{}'::jsonb,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- Child profiles with parental controls
create table public.child_profiles (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  age integer not null check (age >= 3 and age <= 18),
  avatar_color text default 'blue',
  bedtime time,
  wake_time time,
  max_session_length integer default 30,
  allowed_exercise_types text[] default array['breathing', 'mindfulness', 'movement'],
  sound_volume_limits jsonb default '{"min": 0.1, "max": 0.8}'::jsonb,
  total_sessions integer default 0,
  longest_streak integer default 0,
  current_streak integer default 0,
  favorite_exercises text[] default array[]::text[],
  recent_moods jsonb[] default array[]::jsonb[],
  sleep_quality jsonb[] default array[]::jsonb[],
  energy_levels jsonb[] default array[]::jsonb[],
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- Parent-child connections for the tagalong system
create table public.parent_child_connections (
  id uuid default uuid_generate_v4() primary key,
  parent_id uuid references public.profiles(id) on delete cascade not null,
  child_id uuid references public.profiles(id) on delete cascade not null,
  connection_code text not null unique,
  is_active boolean default true,
  connected_at timestamptz default now() not null,
  last_heartbeat timestamptz default now() not null,
  shared_settings jsonb default '{
    "allowParentGuidance": true,
    "shareProgress": true,
    "enableEncouragement": true,
    "sessionSyncMode": "real-time"
  }'::jsonb,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null,
  
  -- Constraints
  constraint unique_parent_child unique (parent_id, child_id),
  constraint different_users check (parent_id != child_id)
);

-- Meditation sessions with real-time sync
create table public.meditation_sessions (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  connection_id uuid references public.parent_child_connections(id) on delete set null,
  session_type text not null,
  start_time timestamptz default now() not null,
  end_time timestamptz,
  planned_duration integer, -- in minutes
  is_active boolean default true,
  progress_data jsonb default '{
    "currentStep": 0,
    "completionPercentage": 0,
    "breathingSync": false,
    "engagementLevel": 1.0,
    "heartRate": null,
    "stressLevel": null
  }'::jsonb,
  completion_data jsonb,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- Real-time messages between parent and child
create table public.realtime_messages (
  id uuid default uuid_generate_v4() primary key,
  connection_id uuid references public.parent_child_connections(id) on delete cascade not null,
  from_parent boolean not null,
  content text not null,
  message_type message_type default 'encouragement',
  acknowledged boolean default false,
  encrypted boolean default false,
  created_at timestamptz default now() not null
);

-- Avatar states for ZenMoon synchronization
create table public.avatar_states (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null unique,
  state_data jsonb not null default '{
    "mood": "neutral",
    "energy": 1.0,
    "expression": "calm",
    "pulseColor": "blue",
    "animationType": "gentle"
  }'::jsonb,
  position_x real,
  position_y real,
  mood text default 'calm',
  pulse_color text default 'blue',
  is_floating boolean default true,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- Activity logs for detailed tracking
create table public.activity_logs (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  activity_type activity_type not null,
  activity_data jsonb not null,
  duration_minutes integer,
  completed boolean default false,
  logged_at timestamptz default now() not null,
  created_at timestamptz default now() not null
);

-- Session participants for group sessions
create table public.session_participants (
  id uuid default uuid_generate_v4() primary key,
  session_id uuid references public.meditation_sessions(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  role text default 'participant',
  joined_at timestamptz default now() not null,
  left_at timestamptz,
  
  constraint unique_session_user unique (session_id, user_id)
);

-- Connection codes for secure pairing
create table public.connection_codes (
  id uuid default uuid_generate_v4() primary key,
  code text not null unique,
  parent_id uuid references public.profiles(id) on delete cascade not null,
  expires_at timestamptz not null,
  used_at timestamptz,
  used_by uuid references public.profiles(id),
  created_at timestamptz default now() not null
);

-- RLS Policies
alter table public.profiles enable row level security;
alter table public.parent_profiles enable row level security;
alter table public.child_profiles enable row level security;
alter table public.parent_child_connections enable row level security;
alter table public.meditation_sessions enable row level security;
alter table public.realtime_messages enable row level security;
alter table public.avatar_states enable row level security;
alter table public.activity_logs enable row level security;
alter table public.session_participants enable row level security;
alter table public.connection_codes enable row level security;

-- Profiles policies
create policy "Users can view own profile" on public.profiles for select using (auth.uid() = id);
create policy "Users can update own profile" on public.profiles for update using (auth.uid() = id);

-- Parent profiles policies
create policy "Parents can manage own profile" on public.parent_profiles for all using (
  exists (select 1 from public.profiles where id = auth.uid() and user_type = 'parent' and id = parent_profiles.user_id)
);

-- Child profiles policies
create policy "Children can view own profile" on public.child_profiles for select using (
  exists (select 1 from public.profiles where id = auth.uid() and user_type = 'child' and id = child_profiles.user_id)
);

create policy "Parents can view connected children profiles" on public.child_profiles for select using (
  exists (
    select 1 from public.parent_child_connections pcc
    join public.profiles p on p.id = auth.uid()
    where pcc.parent_id = auth.uid() 
    and pcc.child_id = child_profiles.user_id 
    and pcc.is_active = true
    and p.user_type = 'parent'
  )
);

-- Connection policies
create policy "Users can view their connections" on public.parent_child_connections for select using (
  parent_id = auth.uid() or child_id = auth.uid()
);

create policy "Parents can create connections" on public.parent_child_connections for insert with check (
  parent_id = auth.uid() and exists (select 1 from public.profiles where id = auth.uid() and user_type = 'parent')
);

-- Sessions policies
create policy "Users can view own sessions" on public.meditation_sessions for select using (user_id = auth.uid());
create policy "Users can create own sessions" on public.meditation_sessions for insert with check (user_id = auth.uid());
create policy "Users can update own sessions" on public.meditation_sessions for update using (user_id = auth.uid());

create policy "Parents can view connected children sessions" on public.meditation_sessions for select using (
  exists (
    select 1 from public.parent_child_connections pcc
    where pcc.parent_id = auth.uid() 
    and pcc.child_id = meditation_sessions.user_id 
    and pcc.is_active = true
  )
);

-- Messages policies
create policy "Users can view connection messages" on public.realtime_messages for select using (
  exists (
    select 1 from public.parent_child_connections pcc
    where pcc.id = realtime_messages.connection_id
    and (pcc.parent_id = auth.uid() or pcc.child_id = auth.uid())
  )
);

create policy "Users can send messages in their connections" on public.realtime_messages for insert with check (
  exists (
    select 1 from public.parent_child_connections pcc
    where pcc.id = connection_id
    and (pcc.parent_id = auth.uid() or pcc.child_id = auth.uid())
  )
);

-- Avatar states policies
create policy "Users can manage own avatar state" on public.avatar_states for all using (user_id = auth.uid());

create policy "Parents can view connected children avatar states" on public.avatar_states for select using (
  exists (
    select 1 from public.parent_child_connections pcc
    where pcc.parent_id = auth.uid() 
    and pcc.child_id = avatar_states.user_id 
    and pcc.is_active = true
  )
);

-- Activity logs policies
create policy "Users can view own activity logs" on public.activity_logs for select using (user_id = auth.uid());
create policy "Users can create own activity logs" on public.activity_logs for insert with check (user_id = auth.uid());

create policy "Parents can view connected children activity logs" on public.activity_logs for select using (
  exists (
    select 1 from public.parent_child_connections pcc
    where pcc.parent_id = auth.uid() 
    and pcc.child_id = activity_logs.user_id 
    and pcc.is_active = true
  )
);

-- Session participants policies
create policy "Users can view sessions they participate in" on public.session_participants for select using (user_id = auth.uid());
create policy "Users can join sessions" on public.session_participants for insert with check (user_id = auth.uid());

-- Connection codes policies
create policy "Parents can manage own connection codes" on public.connection_codes for all using (parent_id = auth.uid());

-- Functions
create or replace function public.generate_connection_code()
returns text
language plpgsql
security definer
as $$
declare
  new_code text;
begin
  -- Generate a 6-digit alphanumeric code
  new_code := upper(substr(md5(random()::text), 1, 6));
  
  -- Ensure uniqueness
  while exists (select 1 from public.connection_codes where code = new_code and expires_at > now()) loop
    new_code := upper(substr(md5(random()::text), 1, 6));
  end loop;
  
  return new_code;
end;
$$;

create or replace function public.create_connection_code(parent_user_id uuid)
returns text
language plpgsql
security definer
as $$
declare
  new_code text;
begin
  -- Verify the user is a parent
  if not exists (select 1 from public.profiles where id = parent_user_id and user_type = 'parent') then
    raise exception 'Only parents can create connection codes';
  end if;
  
  -- Generate new code
  new_code := public.generate_connection_code();
  
  -- Insert the code (expires in 1 hour)
  insert into public.connection_codes (code, parent_id, expires_at)
  values (new_code, parent_user_id, now() + interval '1 hour');
  
  return new_code;
end;
$$;

create or replace function public.connect_with_code(child_user_id uuid, connection_code text)
returns uuid
language plpgsql
security definer
as $$
declare
  parent_user_id uuid;
  connection_id uuid;
begin
  -- Verify the user is a child
  if not exists (select 1 from public.profiles where id = child_user_id and user_type = 'child') then
    raise exception 'Only children can use connection codes';
  end if;
  
  -- Find valid connection code
  select parent_id into parent_user_id
  from public.connection_codes
  where code = connection_code
    and expires_at > now()
    and used_at is null;
  
  if parent_user_id is null then
    raise exception 'Invalid or expired connection code';
  end if;
  
  -- Mark code as used
  update public.connection_codes
  set used_at = now(), used_by = child_user_id
  where code = connection_code;
  
  -- Create connection
  insert into public.parent_child_connections (parent_id, child_id, connection_code)
  values (parent_user_id, child_user_id, connection_code)
  returning id into connection_id;
  
  return connection_id;
end;
$$;

-- Triggers for updated_at
create or replace function public.handle_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger handle_updated_at before update on public.profiles for each row execute procedure public.handle_updated_at();
create trigger handle_updated_at before update on public.parent_profiles for each row execute procedure public.handle_updated_at();
create trigger handle_updated_at before update on public.child_profiles for each row execute procedure public.handle_updated_at();
create trigger handle_updated_at before update on public.parent_child_connections for each row execute procedure public.handle_updated_at();
create trigger handle_updated_at before update on public.meditation_sessions for each row execute procedure public.handle_updated_at();
create trigger handle_updated_at before update on public.avatar_states for each row execute procedure public.handle_updated_at();

-- Trigger to create profile on user signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into public.profiles (id, email, user_type)
  values (new.id, new.email, 'child'); -- Default to child, can be updated
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Indexes for performance
create index idx_profiles_user_type on public.profiles(user_type);
create index idx_connections_parent_id on public.parent_child_connections(parent_id);
create index idx_connections_child_id on public.parent_child_connections(child_id);
create index idx_connections_active on public.parent_child_connections(is_active);
create index idx_sessions_user_id on public.meditation_sessions(user_id);
create index idx_sessions_active on public.meditation_sessions(is_active);
create index idx_messages_connection_id on public.realtime_messages(connection_id);
create index idx_activity_logs_user_id on public.activity_logs(user_id);
create index idx_activity_logs_type on public.activity_logs(activity_type);
create index idx_connection_codes_code on public.connection_codes(code);
create index idx_connection_codes_expires on public.connection_codes(expires_at);
