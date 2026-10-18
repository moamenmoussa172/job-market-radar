-- No job located in Israel (or open only to people there) may reach the marts.
select f.job_id
from {{ ref('fct_job_postings') }} f
join {{ ref('bridge_job_regions') }} b using (job_id)
where b.country = 'Israel'
