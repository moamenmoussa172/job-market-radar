select job_id, skill_id, count(*)
from {{ ref('bridge_job_skills') }}
group by 1, 2
having count(*) > 1
