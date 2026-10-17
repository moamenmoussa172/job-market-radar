-- Workday career sites (myworkdayjobs.com JSON API). Only jobs in MENA + Europe are
-- fetched. Details (description, exact start date, country) exist for the newest
-- jobs of each board; the rest keep the list fields (title, location, "Posted N Days Ago").
with base as ({{ source_snapshots('workday') }}),

shaped as (
    select
        base.*,
        nullif(coalesce(nullif(p ->> 'location', ''), nullif(p ->> 'locationsText', '')), '') as loc1,
        nullif(p ->> 'country', '')                                                          as country_name,
        (select string_agg(l #>> '{}', '; ')
           from jsonb_array_elements(case when jsonb_typeof(p -> 'additionalLocations') = 'array'
                                          then p -> 'additionalLocations' else '[]'::jsonb end) as l)
                                                                                             as more_locs,
        lower(coalesce(p ->> 'remoteType', ''))                                              as remote_type
    from base
),

located as (
    select
        shaped.*,
        nullif(concat_ws(', ',
            loc1,
            case when country_name is not null and position(lower(country_name) in lower(coalesce(loc1, ''))) = 0
                 then country_name end,
            more_locs), '')                                                                   as loc,
        case
            when remote_type like '%hybrid%' or coalesce(loc1, '') ~* 'hybrid' then 'hybrid'
            when remote_type like '%remote%' or coalesce(loc1, '') ~* '\mremote\M' then 'remote'
            when remote_type like '%site%' or remote_type like '%office%' then 'onsite'
        end                                                                                   as wp
    from shaped
)

select
    'workday'::text                                         as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), nullif(p ->> 'company', ''),
             (select case when length(t) <= 3 then upper(t) else initcap(t) end
              from (select split_part(p ->> 'board_token', '.', 1) as t) x))
                                                            as company_name,
    loc                                                     as location_text,
    case wp when 'remote' then true when 'onsite' then false end
                                                            as is_remote_flag,
    wp                                                      as workplace_type,
    case when wp = 'remote' then loc end                    as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'jobDescription'                                  as description_html,
    coalesce({{ safe_timestamp("p ->> 'startDate'") }},
             {{ safe_timestamp("p ->> 'posted_date'") }})   as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'timeType', '')                            as employment_type,
    null::text                                              as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from located
