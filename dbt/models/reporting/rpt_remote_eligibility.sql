-- "Which remote jobs accept people from my region?"
-- A worldwide job counts for every region; a restricted job counts for the
-- regions it names (directly, or via one of its listed countries).
with remote_jobs as (
    select job_id, track, role_family, seniority, remote_scope
    from {{ ref('fct_job_postings') }}
    where is_active and work_mode = 'Remote'
),

regions as (
    select distinct region
    from {{ ref('geo_patterns') }}
),

eligible as (
    -- worldwide jobs -> every region
    select j.job_id, rg.region
    from remote_jobs j
    cross join regions rg
    where j.remote_scope = 'Worldwide'
    union
    -- restricted jobs -> their named regions
    select j.job_id, br.region
    from remote_jobs j
    join {{ ref('bridge_job_regions') }} br using (job_id)
    where j.remote_scope = 'Restricted'
      and br.region <> 'Worldwide'
)

select
    e.region,
    j.track,
    j.role_family,
    j.seniority,
    count(distinct e.job_id)                                              as remote_jobs,
    count(distinct e.job_id) filter (where j.remote_scope = 'Worldwide')  as worldwide_jobs,
    count(distinct e.job_id) filter (where j.remote_scope = 'Restricted') as region_specific_jobs
from eligible e
join remote_jobs j using (job_id)
group by 1, 2, 3, 4
