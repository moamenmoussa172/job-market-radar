-- A job can't be last seen before it was first seen.
select job_id, first_seen_date, last_seen_date
from {{ ref('fct_job_postings') }}
where last_seen_date < first_seen_date
