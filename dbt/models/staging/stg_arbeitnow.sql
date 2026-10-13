-- Arbeitnow: Europe-focused board, onsite and remote. created_at is a unix epoch.
with base as ({{ source_snapshots('arbeitnow') }})

select
    'arbeitnow'::text                                       as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    nullif(trim(p ->> 'company_name'), '')                  as company_name,
    nullif(trim(p ->> 'location'), '')                      as location_text,
    (p ->> 'remote')::boolean                               as is_remote_flag,
    case when (p ->> 'remote')::boolean then 'remote' end   as workplace_type,
    case when (p ->> 'remote')::boolean then nullif(trim(p ->> 'location'), '') end
                                                            as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    {{ safe_timestamp("p ->> 'created_at'") }}              as posted_at,
    p ->> 'url'                                             as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    {{ json_list_to_text("p -> 'job_types'") }}             as employment_type,
    {{ json_list_to_text("p -> 'tags'") }}                  as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
