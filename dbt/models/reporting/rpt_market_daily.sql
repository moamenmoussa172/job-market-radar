-- Market size per day: distinct jobs listed, by role family and work mode.
with daily_listings as (
    select distinct
        s.snapshot_date,
        k.job_id,
        k.role_family,
        k.work_mode
    from {{ source('raw', 'job_posting_snapshots') }} s
    join {{ ref('int_postings_keyed') }} k
      on k.posting_key = md5(s.source || ':' || s.source_job_id)
    where k.role_family <> 'Not a data role'
)

select
    snapshot_date,
    role_family,
    work_mode,
    count(distinct job_id) as jobs_listed
from daily_listings
group by 1, 2, 3
