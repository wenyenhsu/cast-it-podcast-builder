-- personal_feed v3: time-decayed listening scores plus a declared-interest
-- prior. Onboarding picks in profiles.interests act like ~10 minutes of
-- pre-existing listening (600 points) per tag, decaying with the same
-- 7-day half-life from signup, so real behavior overtakes claims after a
-- few episodes and stale claims fade on their own.

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
  order by
    coalesce(es.score, 0) desc,
    ep.publish_date desc nulls last,
    ep.created_at desc;
$$;
