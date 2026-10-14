-- Greenhouse company boards. content is entity-escaped HTML; remote-ness
-- is only in the location text, so is_remote_flag stays NULL here.
with base as ({{ source_snapshots('greenhouse') }})

select
    'greenhouse'::text                                      as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(trim(p ->> 'company_name'), ''), nullif(p ->> 'board_company', ''), p ->> 'board_token')
                                                            as company_name,
    nullif(trim(p -> 'location' ->> 'name'), '')            as location_text,
    null::boolean                                           as is_remote_flag,
    null::text                                              as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'content'                                         as description_html,
    coalesce({{ safe_timestamp("p ->> 'first_published'") }},
             {{ safe_timestamp("p ->> 'updated_at'") }})    as posted_at,
    p ->> 'absolute_url'                                    as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    null::text                                              as employment_type,
    {{ json_list_to_text("p -> 'departments'") }}           as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
