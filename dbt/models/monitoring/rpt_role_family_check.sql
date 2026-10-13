-- Titles that landed in the catch-all role buckets. Review these to
-- improve the role rules in int_postings_classified.sql.
select
    role_family,
    job_title,
    count(*) as postings
from {{ ref('int_postings_classified') }}
where role_family in ('Other data role', 'Other')
group by 1, 2
order by postings desc, job_title
