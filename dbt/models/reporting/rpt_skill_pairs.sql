-- "I know <skill_a>. Which skill most often comes with it?"
-- pct_of_skill_a_jobs = of the active jobs asking for skill_a, the share
-- that also ask for skill_b. The first step toward "next best skill".
with active_skills as (
    select b.job_id, b.skill
    from {{ ref('bridge_job_skills') }} b
    join {{ ref('fct_job_postings') }} f using (job_id)
    where f.is_active
),

skill_totals as (
    select skill, count(distinct job_id) as skill_a_jobs
    from active_skills
    group by 1
)

select
    a.skill                                                        as skill_a,
    b.skill                                                        as skill_b,
    count(distinct a.job_id)                                       as jobs_with_both,
    t.skill_a_jobs,
    round(100.0 * count(distinct a.job_id) / t.skill_a_jobs, 1)    as pct_of_skill_a_jobs
from active_skills a
join active_skills b
  on a.job_id = b.job_id
 and a.skill <> b.skill
join skill_totals t
  on t.skill = a.skill
group by a.skill, b.skill, t.skill_a_jobs
