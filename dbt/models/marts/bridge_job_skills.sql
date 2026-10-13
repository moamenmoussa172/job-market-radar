-- Which skills each job asks for: title + description matched against the
-- skills seed (word-boundary regexes). One row per job x skill.
select distinct
    f.job_id,
    s.skill_id,
    s.skill,
    s.category
from {{ ref('fct_job_postings') }} f
join {{ ref('skills') }} seed
  on (f.job_title || ' ' || coalesce(f.description_text, '')) ~* seed.pattern
join {{ ref('dim_skills') }} s
  on s.skill = seed.skill
