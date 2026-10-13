-- "Where are the jobs?" Active jobs per country, split by work mode.
-- For remote jobs the country is an *eligible* country, not an office.
select
    r.country,
    r.region,
    f.work_mode,
    f.track,
    f.role_family,
    f.seniority,
    count(distinct f.job_id) as jobs
from {{ ref('fct_job_postings') }} f
join {{ ref('bridge_job_regions') }} r using (job_id)
where f.is_active
  and r.country is not null
group by 1, 2, 3, 4, 5, 6
