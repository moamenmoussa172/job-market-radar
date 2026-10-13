-- "I want to be a <role>. What should I learn?"
-- Share of active jobs in each role that mention each skill.
with active as (
    select job_id, track, role_family
    from {{ ref('fct_job_postings') }}
    where is_active
),

role_totals as (
    select track, role_family, count(*) as role_jobs
    from active
    group by 1, 2
)

select
    a.track,
    a.role_family,
    s.skill,
    s.category,
    count(distinct a.job_id)                                         as jobs_with_skill,
    rt.role_jobs,
    round(100.0 * count(distinct a.job_id) / rt.role_jobs, 1)        as pct_of_role_jobs
from active a
join {{ ref('bridge_job_skills') }} s using (job_id)
join role_totals rt using (track, role_family)
group by a.track, a.role_family, s.skill, s.category, rt.role_jobs
