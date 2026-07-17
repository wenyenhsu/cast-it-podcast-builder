-- Manual publish gate: episodes carry publish (0 or 1) and only publish = 1
-- rows are visible to listeners. The pipeline upserts rows with the default 0,
-- so each episode stays hidden until it is explicitly flipped to 1.

alter table public.episodes
  add column publish smallint not null default 0
  check (publish in (0, 1));

-- Rows already on the shelf were live before the gate existed; keep them live.
update public.episodes set publish = 1;

-- Enforce the gate at the RLS layer so every security-invoker read
-- (direct selects, recommended_episodes) only sees published rows.
drop policy "episodes are publicly readable" on public.episodes;

create policy "published episodes are publicly readable"
  on public.episodes for select
  to anon, authenticated
  using (publish = 1);

-- personal_feed is security definer and bypasses RLS, so it must filter
-- explicitly. Same body as v3 (20260708000005) plus the publish gate.
create or replace function public.personal_feed(p_session_id text default '')
returns setof public.episodes
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
  episode_scores as (
    select et.episode_id, sum(coalesce(ts.seconds, 0)) as score
    from public.episode_tags et
    left join tag_scores ts on ts.tag_slug = et.tag_slug
    group by et.episode_id
  )
  select ep.*
  from public.episodes ep
  left join episode_scores es on es.episode_id = ep.id
  where ep.publish = 1
  order by
    coalesce(es.score, 0) desc,
    ep.publish_date desc nulls last,
    ep.created_at desc;
$$;
