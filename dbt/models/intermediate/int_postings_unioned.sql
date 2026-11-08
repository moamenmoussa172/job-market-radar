-- All sources in one shape, plus plain-text description and activity flag.
-- A job is "active" if it appeared in its source's latest snapshot, so one
-- failed source run doesn't mark that source's jobs inactive everywhere.
-- Rotating sources (a different slice of searches each day) can't use that
-- rule: their jobs stay active if seen within the last N days.
{% set sources = ['remotive', 'jobicy', 'remoteok', 'himalayas', 'arbeitnow', 'greenhouse', 'lever', 'ashby',
                  'smartrecruiters', 'workable', 'recruitee', 'personio', 'breezy', 'teamtailor', 'workday', 'successfactors', 'phenom', 'oracle', 'bamboohr', 'pinpoint', 'jsearch', 'jooble', 'adzuna', 'bundesagentur', 'francetravail'] %}
{% set rotating_sources = ['jsearch', 'jooble', 'adzuna', 'bundesagentur', 'francetravail', 'remoteok'] %}  {# remoteok: feed shows only the newest ~100 #}
{% set rotating_active_days = 21 %}  {# > one full search cycle (JSearch: ~16 days) #}
{#- Adzuna goes through all its searches in ~5 days, so 10 days = two full rounds without seeing the job. -#}
{% set short_window = {'adzuna': 10} %}
{#- Search sites keep showing old ads long after the company closed them; past this age we drop them. -#}
{% set search_sources = ['jsearch', 'jooble', 'adzuna', 'remoteok'] %}
{% set search_max_age_days = 30 %}

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
    case when u.source in ('{{ search_sources | join("', '") }}')
              and u.posted_at is not null
              and u.posted_at::date < sl.source_latest_date - {{ search_max_age_days }}
         then false                                -- old search-site ad: usually closed already
         {% for src, days in short_window.items() %}
         when u.source = '{{ src }}'
         then u.last_seen_date >= sl.source_latest_date - {{ days }}
         {% endfor %}
         when u.source in ('{{ rotating_sources | join("', '") }}')
         then u.last_seen_date >= sl.source_latest_date - {{ rotating_active_days }}
         else u.last_seen_date >= sl.source_latest_date
    end                                            as is_active
from unioned u
join source_latest sl using (source)
where u.job_title is not null
