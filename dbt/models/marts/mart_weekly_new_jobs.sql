-- Hiring trend: new tech jobs per week, by place (scope) and track.
-- "New" = first seen that week. Jobs we saw on the first day we read a source - or, for
-- company boards, the first day we read that company - were already open before: they are
-- backlog, not new hiring, and are left out (otherwise adding a source looks like a boom).
-- scope = 'All' | 'Remote' | a country (office and hybrid jobs located there).
{% set board_sources = ['greenhouse', 'lever', 'ashby', 'smartrecruiters', 'workable', 'recruitee',
                        'personio', 'breezy', 'teamtailor', 'workday', 'successfactors', 'phenom', 'oracle'] %}
with f as (
    select * from {{ ref('fct_job_postings') }}
    where coalesce(track, '') <> 'Not tech'
),

source_start as (
    select primary_source, min(first_seen_date) as start_date from f group by 1
),

company_start as (
    select primary_source, lower(company_name) as company, min(first_seen_date) as start_date
    from f group by 1, 2
),

new_jobs as (
    select f.job_id, f.track, f.work_mode, date_trunc('week', f.first_seen_date)::date as week_start
    from f
    join source_start ss using (primary_source)
    left join company_start cs
      on cs.primary_source = f.primary_source and cs.company = lower(f.company_name)
    where f.first_seen_date > ss.start_date
      and not (f.primary_source in ('{{ board_sources | join("', '") }}')
               and f.first_seen_date = cs.start_date)
),

scoped as (
    select job_id, track, week_start, 'All'::text as scope from new_jobs
    union all
    select job_id, track, week_start, 'Remote' from new_jobs where work_mode = 'Remote'
    union all
    select distinct n.job_id, n.track, n.week_start, b.country
    from new_jobs n
    join {{ ref('bridge_job_regions') }} b using (job_id)
    where b.country is not null and n.work_mode <> 'Remote'
)

select week_start, scope, track, count(distinct job_id) as new_jobs
from scoped
group by 1, 2, 3
