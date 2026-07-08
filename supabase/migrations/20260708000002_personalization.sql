-- Personalized feed and listener profiles.

-- Auto-create a profile row when a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1))
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Feed ordered by how much the caller has listened to each category.
-- Listening time is estimated from activity events: each 30s heartbeat
-- counts fully, completes add a bonus, plays a nudge. Works for both
-- logged-in users (auth.uid()) and anonymous sessions (p_session_id).
-- SECURITY DEFINER so it can aggregate activity_events (whose rows are
-- not directly readable); it only ever exposes the caller's own signal,
-- already aggregated per category.
create or replace function public.personal_feed(p_session_id text default '')
returns setof public.episodes
language sql
stable
security definer
set search_path = public
as $$
  with listened as (
    select e.category,
           sum(
             case a.type
               when 'episode_progress' then 30
               when 'episode_complete' then 60
               when 'episode_play' then 5
               else 0
             end
           ) as seconds
    from public.activity_events a
    join public.episodes e on e.id = a.episode_id
    where e.category <> ''
      and (
        (auth.uid() is not null and a.user_id = auth.uid())
        or (p_session_id <> '' and a.session_id = p_session_id)
      )
    group by e.category
  )
  select ep.*
  from public.episodes ep
  left join listened l on l.category = ep.category
  order by
    coalesce(l.seconds, 0) desc,
    ep.publish_date desc nulls last,
    ep.created_at desc;
$$;
