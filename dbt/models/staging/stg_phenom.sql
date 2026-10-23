-- Phenom career sites (e.g. orange.jobs), read through the site's own job search (POST /widgets).
-- The listing has a short teaser, not the full description; location is "City, State, Country".
with base as ({{ source_snapshots('phenom') }})

select
    'phenom'::text                                          as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), nullif(p ->> 'companyName', ''),
             initcap(split_part(split_part(p ->> 'board_token', '/', 1), '.', 1)))
                                                            as company_name,
    coalesce(nullif(p ->> 'location', ''),
             nullif(concat_ws(', ', nullif(p ->> 'city', ''), nullif(p ->> 'state', ''), nullif(p ->> 'country', '')), ''))
                                                            as location_text,
    case when concat(p ->> 'location', ' ', p ->> 'title', ' ', p ->> 'type') ~* '\mremote\M' then true end
                                                            as is_remote_flag,
    case when concat(p ->> 'location', ' ', p ->> 'title') ~* '\mhybrid\M' then 'hybrid'
         when concat(p ->> 'location', ' ', p ->> 'title', ' ', p ->> 'type') ~* '\mremote\M' then 'remote' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    coalesce(p ->> 'descriptionTeaser', p ->> 'description') as description_html,
    {{ safe_timestamp("left(coalesce(p ->> 'postedDate', p ->> 'dateCreated'), 19)") }}
                                                            as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    nullif(p ->> 'experienceLevel', '')                     as seniority_hint,
    nullif(p ->> 'type', '')                                as employment_type,
    nullif(p ->> 'category', '')                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
