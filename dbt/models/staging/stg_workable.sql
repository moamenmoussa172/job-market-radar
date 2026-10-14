-- Workable company boards (public account API with details=true).
-- telecommuting = remote; country is a name; description is HTML.
with base as ({{ source_snapshots('workable') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ', nullif(p ->> 'city', ''), nullif(p ->> 'state', ''), nullif(p ->> 'country', '')), '') as loc,
        case
            when lower(coalesce(p ->> 'workplace', p ->> 'workplace_type', '')) like '%hybrid%' then 'hybrid'
            when (p ->> 'telecommuting')::boolean
              or lower(coalesce(p ->> 'workplace', p ->> 'workplace_type', '')) like '%remote%' then 'remote'
            when lower(coalesce(p ->> 'workplace', p ->> 'workplace_type', '')) ~ 'on.?site' then 'onsite'
        end as wp
    from base
)

select
    'workable'::text                                        as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(trim(p ->> 'account_name'), ''), nullif(p ->> 'board_company', ''), p ->> 'board_token')
                                                            as company_name,
    loc                                                     as location_text,
    case wp when 'remote' then true when 'onsite' then false end
                                                            as is_remote_flag,
    wp                                                      as workplace_type,
    case when wp = 'remote' then loc end                    as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    coalesce({{ safe_timestamp("p ->> 'published_on'") }},
             {{ safe_timestamp("left(p ->> 'created_at', 19)") }})
                                                            as posted_at,
    coalesce(p ->> 'url', p ->> 'shortlink', p ->> 'application_url')
                                                            as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    nullif(p ->> 'experience', '')                          as seniority_hint,
    nullif(p ->> 'employment_type', '')                     as employment_type,
    nullif(concat_ws(', ', nullif(p ->> 'department', ''), nullif(p ->> 'function', '')), '')
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
