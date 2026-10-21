-- Remote OK: remote-only feed (newest ~100 jobs). "location" is free text: usually who may
-- apply ("Worldwide", "United States", "Europe"), sometimes an office city.
-- Salaries are 0 when not given. Terms: link back to the Remote OK page (job_url), credit Remote OK.
with base as ({{ source_snapshots('remoteok') }})

select
    'remoteok'::text                                        as source,
    source_job_id,
    nullif(trim(p ->> 'position'), '')                      as job_title,
    nullif(trim(p ->> 'company'), '')                       as company_name,
    nullif(trim(both ', ' from p ->> 'location'), '')       as location_text,
    true                                                    as is_remote_flag,
    'remote'::text                                          as workplace_type,
    nullif(trim(both ', ' from p ->> 'location'), '')       as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    {{ safe_timestamp("p ->> 'date'") }}                    as posted_at,
    p ->> 'url'                                             as job_url,
    nullif({{ safe_numeric("p ->> 'salary_min'") }}, 0)     as salary_min,
    nullif({{ safe_numeric("p ->> 'salary_max'") }}, 0)     as salary_max,
    case when coalesce({{ safe_numeric("p ->> 'salary_max'") }}, 0) > 0 then 'USD' end as salary_currency,
    case when coalesce({{ safe_numeric("p ->> 'salary_max'") }}, 0) > 0 then 'year' end as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    null::text                                              as employment_type,
    {{ json_list_to_text("p -> 'tags'") }}                  as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
