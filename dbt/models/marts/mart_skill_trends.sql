-- Skill momentum: the share of open jobs that ask for each skill, today vs N days ago,
-- per place (scope). N = half the history we have, between 7 and 28 days.
-- A job was open on day d if we first saw it on/before d and last saw it on/after d
-- (rotating search sources revisit a search only every few weeks, so for them "last seen
-- within 21 days" counts as still open - the same rule as is_active).
{% set rotating_sources = ['jsearch', 'jooble', 'adzuna', 'bundesagentur', 'remoteok'] %}
with f as (
    select job_id, work_mode, first_seen_date,
           last_seen_date + case when primary_source in ('{{ rotating_sources | join("', '") }}')
                                 then 21 else 0 end as open_until
    from {{ ref('fct_job_postings') }}
    where coalesce(track, '') <> 'Not tech'
),

win as (
    select max(first_seen_date) as today,
           greatest(7, least(28, (max(first_seen_date) - min(first_seen_date)) / 2)) as window_days
    from f
),

snap as (
    select f.job_id, f.work_mode, p.period
    from f
    cross join win
    cross join lateral (values ('now', win.today), ('before', win.today - win.window_days)) as p(period, d)
    where f.first_seen_date <= p.d and f.open_until >= p.d
),

scoped as (
    select job_id, period, 'All'::text as scope from snap
    union all
    select job_id, period, 'Remote' from snap where work_mode = 'Remote'
    union all
    select distinct s.job_id, s.period, b.country
    from snap s
    join {{ ref('bridge_job_regions') }} b using (job_id)
    where b.country is not null and s.work_mode <> 'Remote'
),

totals as (
    select scope, period, count(distinct job_id) as jobs from scoped group by 1, 2
),

skill_counts as (
    select s.scope, s.period, k.skill, count(distinct s.job_id) as jobs
    from scoped s
    join {{ ref('bridge_job_skills') }} k using (job_id)
    group by 1, 2, 3
),

wide as (
    select
        t_now.scope,
        k.skill,
        coalesce(max(case when k.period = 'now' then k.jobs end), 0)    as jobs_now,
        t_now.jobs                                                       as total_now,
        coalesce(max(case when k.period = 'before' then k.jobs end), 0) as jobs_before,
        t_before.jobs                                                    as total_before
    from skill_counts k
    join totals t_now    on t_now.scope = k.scope and t_now.period = 'now'
    join totals t_before on t_before.scope = k.scope and t_before.period = 'before'
    group by t_now.scope, k.skill, t_now.jobs, t_before.jobs
)

select
    w.scope,
    w.skill,
    win.window_days,
    w.jobs_now,
    w.total_now,
    w.jobs_before,
    w.total_before,
    round(100.0 * w.jobs_now / w.total_now, 1)                                  as share_now_pct,
    round(100.0 * w.jobs_before / w.total_before, 1)                            as share_before_pct,
    round(100.0 * w.jobs_now / w.total_now - 100.0 * w.jobs_before / w.total_before, 1) as change_pts
from wide w
cross join win
where w.total_now >= 30 and w.total_before >= 30      -- too few jobs: no trend
  and w.jobs_now + w.jobs_before >= 5
