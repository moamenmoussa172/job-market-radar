-- Breezy HR careers sites (<company>.breezy.hr/json). The feed lists open positions with
-- location, remote flag, type and department, but no descriptions (so no skills).
-- The company's country from the board list (board_country) helps the geo rules.
with base as ({{ source_snapshots('breezy') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ',
            coalesce(nullif(p #>> '{location,name}', ''), nullif(p #>> '{location,city}', '')),
            nullif(p #>> '{location,country,name}', ''),
            case when coalesce(p #>> '{location,country,name}', '') = '' then nullif(p ->> 'board_country', '') end), '')
                                                                          as loc,
        (p #>> '{location,is_remote}') = 'true'                           as remote
    from base
)

select
    'breezy'::text                                          as source,
    source_job_id,
    nullif(trim(p ->> 'name'), '')                          as job_title,
    coalesce(nullif(p ->> 'board_company', ''), nullif(p #>> '{company,name}', ''),
             initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    loc                                                     as location_text,
    remote                                                  as is_remote_flag,
    case when remote then 'remote' end                      as workplace_type,
    case when remote then loc end                           as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    null::text                                              as description_html,
    {{ safe_timestamp("p ->> 'published_date'") }}          as posted_at,
    p ->> 'url'                                             as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    nullif(p ->> 'salary', '')                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p #>> '{type,name}', '')                         as employment_type,
    nullif(p ->> 'department', '')                          as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
