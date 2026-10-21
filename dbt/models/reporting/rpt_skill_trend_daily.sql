-- "Which skills are rising?" For every snapshot day: how many distinct jobs
-- that were listed that day ask for each skill. Fills in as days accumulate.
with daily_listings as (
    select distinct
        s.snapshot_date,
        k.job_id
    from {{ source('raw', 'job_posting_snapshots') }} s
    join {{ ref('int_postings_keyed') }} k
      on k.posting_key = md5(s.source || ':' || s.source_job_id)
    -- rotating sources search different countries each day, so they'd make
    -- day-to-day numbers jump; trends use the full-feed sources only
    where s.source not in ('jsearch', 'jooble', 'adzuna', 'bundesagentur', 'remoteok')
),

daily_totals as (
    select snapshot_date, count(distinct job_id) as jobs_listed
    from daily_listings
    group by 1
)

select
    d.snapshot_date,
    b.skill,
    b.category,
    count(distinct d.job_id)                                       as jobs_with_skill,
    t.jobs_listed,
    round(100.0 * count(distinct d.job_id) / t.jobs_listed, 1)     as pct_of_jobs
from daily_listings d
join {{ ref('bridge_job_skills') }} b using (job_id)
join daily_totals t using (snapshot_date)
group by d.snapshot_date, b.skill, b.category, t.jobs_listed
