-- All sources in one shape, plus plain-text description and activity flag.
-- A job is "active" if it appeared in its source's latest snapshot, so one
-- failed source run doesn't mark that source's jobs inactive everywhere.
{% set sources = ['remotive', 'jobicy', 'himalayas', 'arbeitnow', 'greenhouse', 'lever', 'ashby'] %}

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
    u.last_seen_date >= sl.source_latest_date      as is_active
from unioned u
join source_latest sl using (source)
where u.job_title is not null
