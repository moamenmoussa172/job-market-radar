-- JSearch (Google for Jobs): postings originally published on LinkedIn, Indeed,
-- Glassdoor, Bayt, company sites... job_country is an ISO-2 code. Salary has
-- no currency field, so it is kept as text only (never converted).
with base as ({{ source_snapshots('jsearch') }}),

shaped as (
    select
        base.*,
        cc.country as country_name,
        nullif(concat_ws(', ', p ->> 'job_city', p ->> 'job_state', cc.country), '') as loc,
        case
            when lower(coalesce(p ->> 'work_arrangement', '')) like '%hybrid%' then 'hybrid'
            when (p ->> 'job_is_remote')::boolean then 'remote'
            when lower(coalesce(p ->> 'work_arrangement', '')) like '%remote%' then 'remote'
            when lower(coalesce(p ->> 'work_arrangement', '')) ~ 'on.?site|office' then 'onsite'
        end as wp
    from base
    left join {{ ref('country_codes') }} cc
      on cc.code = upper(p ->> 'job_country')
)

select
    'jsearch'::text                                         as source,
    source_job_id,
    nullif(trim(p ->> 'job_title'), '')                     as job_title,
    nullif(trim(p ->> 'employer_name'), '')                 as company_name,
    coalesce(loc, p ->> 'job_location')                     as location_text,
    case wp when 'remote' then true when 'onsite' then false end
                                                            as is_remote_flag,
    wp                                                      as workplace_type,
    case when wp = 'remote' then coalesce(loc, p ->> 'job_location') end
                                                            as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'job_description'                                 as description_html,
    coalesce({{ safe_timestamp("p ->> 'job_posted_at_datetime_utc'") }},
             {{ safe_timestamp("p ->> 'job_posted_at_timestamp'") }})
                                                            as posted_at,
    coalesce(p ->> 'job_apply_link', p ->> 'job_google_link')
                                                            as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    nullif(coalesce(p ->> 'job_salary_string', p ->> 'job_salary'), '')
                                                            as salary_text,
    nullif(p ->> 'seniority_level', '')                     as seniority_hint,
    nullif(p ->> 'job_employment_type', '')                 as employment_type,
    nullif(p ->> 'job_publisher', '')                       as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
