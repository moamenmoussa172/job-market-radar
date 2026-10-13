select
    md5(lower(skill)) as skill_id,
    skill,
    category
from {{ ref('skills') }}
