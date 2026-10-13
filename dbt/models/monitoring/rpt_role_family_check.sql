-- Titles that landed in the catch-all role buckets (per track). Review these to
-- improve the role rules in int_postings_classified.sql.
select
    track,
    role_family,
    job_title,
    count(*) as postings
from {{ ref('int_postings_classified') }}
where role_family in ('Other data role', 'Other tech role')
group by 1, 2, 3
order by postings desc, job_title
