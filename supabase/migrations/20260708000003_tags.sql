-- Fixed tag taxonomy for episodes; interest ranking moves from the single
-- category to per-episode tags (max 3, pushed by the local publisher).

create table public.tags (
  slug text primary key,
  name text not null unique
);

create table public.episode_tags (
  episode_id uuid not null references public.episodes (id) on delete cascade,
  tag_slug text not null references public.tags (slug) on delete cascade,
  primary key (episode_id, tag_slug)
);

create index episode_tags_tag_idx on public.episode_tags (tag_slug);

alter table public.tags enable row level security;
alter table public.episode_tags enable row level security;

create policy "tags are publicly readable"
  on public.tags for select to anon, authenticated using (true);

create policy "episode tags are publicly readable"
  on public.episode_tags for select to anon, authenticated using (true);

-- Seed the taxonomy (mirrors ALLOWED_TAGS in the backend).
insert into public.tags (slug, name) values
  ('algorithms', 'Algorithms'),
  ('llm', 'LLM'),
  ('claude-fable', 'Claude Fable'),
  ('machine-learning', 'Machine Learning'),
  ('data-science', 'Data Science'),
  ('infrastructure', 'Infrastructure'),
  ('networking', 'Networking'),
  ('security', 'Security'),
  ('privacy', 'Privacy'),
  ('uiux', 'UI/UX'),
  ('web-development', 'Web Development'),
  ('mobile', 'Mobile'),
  ('cloud', 'Cloud'),
  ('devops', 'DevOps'),
  ('databases', 'Databases'),
  ('programming-languages', 'Programming Languages'),
  ('open-source', 'Open Source'),
  ('hardware', 'Hardware'),
  ('robotics', 'Robotics'),
  ('startups', 'Startups')
on conflict (slug) do nothing;

-- personal_feed v2: score per tag instead of per category. An episode's
-- rank is the sum of the caller's listening seconds across the tags it
-- shares; category remains only as metadata.
create or replace function public.personal_feed(p_session_id text default '')
returns setof public.episodes
language sql
stable
security definer
set search_path = public
as $$
  with listened_tags as (
    select et.tag_slug,
           sum(
             case a.type
               when 'episode_progress' then 30
               when 'episode_complete' then 60
               when 'episode_play' then 5
               else 0
             end
           ) as seconds
    from public.activity_events a
    join public.episode_tags et on et.episode_id = a.episode_id
    where
      (auth.uid() is not null and a.user_id = auth.uid())
      or (p_session_id <> '' and a.session_id = p_session_id)
    group by et.tag_slug
  ),
  episode_scores as (
    select et.episode_id, sum(coalesce(lt.seconds, 0)) as score
    from public.episode_tags et
    left join listened_tags lt on lt.tag_slug = et.tag_slug
    group by et.episode_id
  )
  select ep.*
  from public.episodes ep
  left join episode_scores es on es.episode_id = ep.id
  order by
    coalesce(es.score, 0) desc,
    ep.publish_date desc nulls last,
    ep.created_at desc;
$$;
