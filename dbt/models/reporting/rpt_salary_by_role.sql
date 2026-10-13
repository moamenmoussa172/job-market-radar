-- "What does this role pay?" Annual USD for active jobs that post a
-- plausible salary. Mostly US postings (pay-transparency laws), so read
-- these as US-market ranges; job counts show how solid each number is.
with s as (
    select track, role_family, seniority, work_mode, salary_annual_mid_usd as mid_usd
    from {{ ref('fct_job_postings') }}
    where is_active and has_comparable_salary
),

totals as (
    select role_family, count(*) as active_jobs
    from {{ ref('fct_job_postings') }}
    where is_active
    group by 1
)

select
    s.track,
    s.role_family,
    s.seniority,
    count(*)                                                              as jobs_with_salary,
    max(t.active_jobs)                                                    as active_jobs_in_role,
    round(percentile_cont(0.25) within group (order by s.mid_usd)::numeric, -3) as p25_usd,
    round(percentile_cont(0.50) within group (order by s.mid_usd)::numeric, -3) as median_usd,
    round(percentile_cont(0.75) within group (order by s.mid_usd)::numeric, -3) as p75_usd
from s
join totals t using (role_family)
group by grouping sets ((s.track, s.role_family), (s.track, s.role_family, s.seniority))
