-- Personio company boards (public XML job feed, parsed to JSON at extraction).
-- Only an office city is given, so the company's country from the company list
-- (board_country) is appended to help the geo rules. No remote flag or salary.
with base as ({{ source_snapshots('personio') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ',
            nullif(p ->> 'office', ''),
            (select string_agg(o #>> '{}', ', ')
               from jsonb_array_elements(case when jsonb_typeof(p -> 'additionalOffices') = 'array'
                                              then p -> 'additionalOffices' else '[]'::jsonb end) as o),
            nullif(p ->> 'board_country', '')), '')                       as loc,
        (select string_agg(concat('<h3>', d ->> 'name', '</h3>', d ->> 'value'), ' ')
           from jsonb_array_elements(case when jsonb_typeof(p -> 'jobDescriptions') = 'array'
                                          then p -> 'jobDescriptions' else '[]'::jsonb end) as d)
                                                                          as descr
    from base
)

select
    'personio'::text                                        as source,
    source_job_id,
    nullif(trim(p ->> 'name'), '')                          as job_title,
    coalesce(nullif(p ->> 'board_company', ''), nullif(p ->> 'subcompany', ''),
             initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    loc                                                     as location_text,
    case when loc ~* 'remote' then true end                 as is_remote_flag,
    case when loc ~* 'remote' then 'remote' end             as workplace_type,
    case when loc ~* 'remote' then loc end                  as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    descr                                                   as description_html,
    {{ safe_timestamp("p ->> 'createdAt'") }}               as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    nullif(p ->> 'seniority', '')                           as seniority_hint,
    nullif(concat_ws(', ', nullif(p ->> 'employmentType', ''), nullif(p ->> 'schedule', '')), '')
                                                            as employment_type,
    nullif(concat_ws(', ', nullif(p ->> 'department', ''), nullif(p ->> 'recruitingCategory', '')), '')
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
