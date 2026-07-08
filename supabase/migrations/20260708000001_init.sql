-- Cast It — public data shelf for the listener frontend.
-- Local pipeline (service_role) writes; the frontend (anon/authenticated) reads.

create extension if not exists vector;

-- ── Episodes ──────────────────────────────────────────────────────────────
-- Published episodes only; the local pipeline pushes rows when audio is final.
create table public.episodes (
  id uuid primary key,
  title text not null,
  description text not null default '',
  summary text not null default '',
  language text not null default 'en',
  publish_date timestamptz,
  duration_seconds integer,
  audio_url text not null,
  cover_url text,
  category text not null default '',
  embedding vector(768),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.episodes enable row level security;

create policy "episodes are publicly readable"
  on public.episodes for select
  to anon, authenticated
  using (true);

-- ── Listener profiles ─────────────────────────────────────────────────────
create table public.profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default '',
  interests jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "users read own profile"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy "users insert own profile"
  on public.profiles for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy "users update own profile"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- ── Listening activity ────────────────────────────────────────────────────
-- Frontend posts play/pause/heartbeat/complete events; local jobs read them
-- (service_role) to derive interests. Not readable by the public.
create table public.activity_events (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users (id) on delete set null,
  session_id text not null,
  episode_id uuid not null,
  type text not null check (type in (
    'episode_play', 'episode_pause', 'episode_seek',
    'episode_progress', 'episode_complete', 'episode_open'
  )),
  position_seconds integer,
  duration_seconds integer,
  occurred_at timestamptz not null,
  inserted_at timestamptz not null default now()
);

create index activity_events_episode_idx on public.activity_events (episode_id);
create index activity_events_session_idx on public.activity_events (session_id);
create index activity_events_user_idx on public.activity_events (user_id);

alter table public.activity_events enable row level security;

create policy "anyone can record activity"
  on public.activity_events for insert
  to anon, authenticated
  with check (true);

-- ── Tier-1 recommendations: completion-weighted category affinity ─────────
create or replace function public.recommended_episodes(
  p_session_id text,
  p_limit integer default 10
)
returns setof public.episodes
language sql
stable
security invoker
as $$
  with listened as (
    select episode_id,
           max((type = 'episode_complete')::int) as completed
    from public.activity_events
    where session_id = p_session_id
    group by episode_id
  ),
  affinity as (
    select e.category, sum(1 + l.completed * 2) as score
    from listened l
    join public.episodes e on e.id = l.episode_id
    where e.category <> ''
    group by e.category
  )
  select e.*
  from public.episodes e
  left join affinity a on a.category = e.category
  where e.id not in (select episode_id from listened where completed = 1)
  order by coalesce(a.score, 0) desc, e.publish_date desc nulls last
  limit p_limit;
$$;
