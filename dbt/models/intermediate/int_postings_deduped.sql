-- The same job is often listed on several boards (and sometimes twice on
-- one board). Keep the richest source as the survivor and merge lifecycles.
with keyed as (select * from {{ ref('int_postings_keyed') }}),

ranked as (
    select
        keyed.*,
        row_number() over (
            partition by job_id
            order by source_priority, last_seen_date desc, posting_key
        ) as rn,
        count(*)               over (partition by job_id) as listing_count,
        min(first_seen_date)   over (partition by job_id) as job_first_seen_date,
        max(last_seen_date)    over (partition by job_id) as job_last_seen_date,
        bool_or(is_active)     over (partition by job_id) as job_is_active
    from keyed
),

source_lists as (
    select job_id, string_agg(distinct source, ', ' order by source) as listed_on
    from keyed
    group by 1
)

select
    r.*,
    s.listed_on
from ranked r
join source_lists s using (job_id)
where r.rn = 1
