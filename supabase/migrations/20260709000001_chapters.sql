-- Chapter pool for personalized feeds.
--
-- The local pipeline builds one standalone MP3 per article ("chapter") in
-- addition to the full stitched episode. Chapters are the shared building
-- blocks of personalization: generated once per day, selected per listener
-- by tag affinity. personal_chapters() returns a listener's daily lineup.

-- ── Chapters ──────────────────────────────────────────────────────────────
create table public.chapters (
  id uuid primary key,                    -- backend chapter AudioAsset id
  episode_id uuid not null references public.episodes (id) on delete cascade,
  article_id uuid not null,
  position integer not null default 1,    -- order within the source episode
  title text not null,
  summary text not null default '',
  category text not null default '',
  duration_seconds integer,
  audio_url text not null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index chapters_episode_idx on public.chapters (episode_id);
create index chapters_published_idx on public.chapters (published_at desc);

alter table public.chapters enable row level security;

create policy "chapters are publicly readable"
  on public.chapters for select
  to anon, authenticated
  using (true);

-- ── Chapter tags ──────────────────────────────────────────────────────────
create table public.chapter_tags (
  chapter_id uuid not null references public.chapters (id) on delete cascade,
  tag_slug text not null references public.tags (slug) on delete cascade,
  primary key (chapter_id, tag_slug)
);

create index chapter_tags_tag_idx on public.chapter_tags (tag_slug);

alter table public.chapter_tags enable row level security;

create policy "chapter tags are publicly readable"
  on public.chapter_tags for select
  to anon, authenticated
  using (true);

-- ── Personalized chapter lineup ───────────────────────────────────────────
-- Same scoring model as personal_feed v3 (time-decayed listening + declared
-- interest prior), applied to recent chapters. Returns the listener's daily
-- lineup: the freshest chapters that best match their tag affinity.
create or replace function public.personal_chapters(
  p_session_id text default '',
  p_limit integer default 5,
  p_days integer default 3
)
returns setof public.chapters
language sql
stable
security definer
set search_path = public
as $$
  with behavioral as (
    select et.tag_slug,
           sum(
             (case a.type
                when 'episode_progress' then 30
                when 'episode_complete' then 60
                when 'episode_play' then 5
                else 0
              end)
             * power(
                 0.5,
                 greatest(extract(epoch from (now() - a.occurred_at)), 0)
                   / (7 * 86400.0)
               )
           ) as seconds
    from public.activity_events a
    join public.episode_tags et on et.episode_id = a.episode_id
    where
      (auth.uid() is not null and a.user_id = auth.uid())
      or (p_session_id <> '' and a.session_id = p_session_id)
    group by et.tag_slug
  ),
  declared as (
    select jsonb_array_elements_text(p.interests) as tag_slug,
           600 * power(
             0.5,
             greatest(extract(epoch from (now() - p.created_at)), 0)
               / (7 * 86400.0)
           ) as seconds
    from public.profiles p
    where auth.uid() is not null and p.user_id = auth.uid()
  ),
  tag_scores as (
    select coalesce(b.tag_slug, d.tag_slug) as tag_slug,
           coalesce(b.seconds, 0) + coalesce(d.seconds, 0) as seconds
    from behavioral b
    full outer join declared d on d.tag_slug = b.tag_slug
  ),
  chapter_scores as (
    select ct.chapter_id, sum(coalesce(ts.seconds, 0)) as score
    from public.chapter_tags ct
    left join tag_scores ts on ts.tag_slug = ct.tag_slug
    group by ct.chapter_id
  )
  select c.*
  from public.chapters c
  left join chapter_scores cs on cs.chapter_id = c.id
  where c.published_at >= now() - make_interval(days => p_days)
  order by
    coalesce(cs.score, 0) desc,
    c.published_at desc nulls last,
    c.position asc
  limit p_limit;
$$;
