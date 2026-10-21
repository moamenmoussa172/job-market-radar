-- How long jobs stay open, by role: days from posting (or from when we first saw it) to the
-- last day it was listed, for jobs that have closed. Only sources we read every day count
-- (a rotating search can't tell when a job closed), and jobs whose start we don't know
-- (already open when we started and no posting date) are left out.
{% set rotating_sources = ['jsearch', 'jooble', 'adzuna', 'bundesagentur', 'remoteok'] %}
with f as (
    select * from {{ ref('fct_job_postings') }}
    where coalesce(track, '') <> 'Not tech'
      and not is_active
      and primary_source not in ('{{ rotating_sources | join("', '") }}')
),

source_start as (
    select primary_source, min(first_seen_date) as start_date
    from {{ ref('fct_job_postings') }}
    group by 1
),

closed as (
    select
        f.track,
        f.role_family,
        f.last_seen_date - coalesce(
            case when f.posted_at::date between f.first_seen_date - 45 and f.first_seen_date
                 then f.posted_at::date end,
            case when f.first_seen_date > ss.start_date then f.first_seen_date end) + 1 as days_open
    from f
    join source_start ss using (primary_source)
)

select
    track,
    role_family,
    count(*)                                                        as closed_jobs,
    percentile_cont(0.5)  within group (order by days_open)::int    as median_days_open,
    percentile_cont(0.25) within group (order by days_open)::int    as p25_days_open,
    percentile_cont(0.75) within group (order by days_open)::int    as p75_days_open
from closed
where days_open is not null and days_open > 0
group by 1, 2
having count(*) >= 5
