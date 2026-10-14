-- All sources in one shape, plus plain-text description and activity flag.
-- A job is "active" if it appeared in its source's latest snapshot, so one
-- failed source run doesn't mark that source's jobs inactive everywhere.
-- Rotating sources (a different slice of searches each day) can't use that
-- rule: their jobs stay active if seen within the last N days.
{% set sources = ['remotive', 'jobicy', 'himalayas', 'arbeitnow', 'greenhouse', 'lever', 'ashby',
                  'smartrecruiters', 'workable', 'recruitee', 'personio', 'jsearch', 'jooble', 'adzuna'] %}
{% set rotating_sources = ['jsearch', 'jooble', 'adzuna'] %}
{% set rotating_active_days = 21 %}  {# > one full search cycle (JSearch: ~16 days) #}

with unioned as (
    {% for s in sources %}
    select * from {{ ref('stg_' ~ s) }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),

source_latest as (
    select source, max(last_seen_date) as source_latest_date
    from unioned
    group by 1
)

select
    md5(u.source || ':' || u.source_job_id)        as posting_key,
    u.*,
    {{ html_to_text('u.description_html') }}       as description_text,
    case when u.source in ('{{ rotating_sources | join("', '") }}')
         then u.last_seen_date >= sl.source_latest_date - {{ rotating_active_days }}
         else u.last_seen_date >= sl.source_latest_date
    end                                            as is_active
from unioned u
join source_latest sl using (source)
where u.job_title is not null
