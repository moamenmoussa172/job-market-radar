-- Jooble aggregator. Descriptions are short snippets (fewer skills detected);
-- location is free text; salary is free text only.
with base as ({{ source_snapshots('jooble') }})

select
    'jooble'::text                                          as source,
    source_job_id,
    nullif(trim(regexp_replace(p ->> 'title', '<[^>]*>', '', 'g')), '')
                                                            as job_title,
    nullif(trim(p ->> 'company'), '')                       as company_name,
    nullif(concat_ws(', ', nullif(trim(p ->> 'location'), ''), p ->> 'search_location'), '')
                                                            as location_text,
    case when (p ->> 'location') ~* 'remote' or (p ->> 'type') ~* 'remote' then true end
                                                            as is_remote_flag,
    case when (p ->> 'location') ~* 'remote' or (p ->> 'type') ~* 'remote' then 'remote' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'snippet'                                         as description_html,
    {{ safe_timestamp("left(p ->> 'updated', 19)") }}       as posted_at,
    p ->> 'link'                                            as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    nullif(p ->> 'salary', '')                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'type', '')                                as employment_type,
    nullif(p ->> 'source', '')                              as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
