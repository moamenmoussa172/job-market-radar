-- Jobicy: remote-only board. jobGeo = eligibility (e.g. "Anywhere", "USA", "EMEA").
with base as ({{ source_snapshots('jobicy') }})

select
    'jobicy'::text                                          as source,
    source_job_id,
    nullif(trim(p ->> 'jobTitle'), '')                      as job_title,
    nullif(trim(p ->> 'companyName'), '')                   as company_name,
    {{ json_list_to_text("p -> 'jobGeo'") }}                as location_text,
    true                                                    as is_remote_flag,
    null::text                                              as workplace_type,
    {{ json_list_to_text("p -> 'jobGeo'") }}                as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'jobDescription'                                  as description_html,
    {{ safe_timestamp("p ->> 'pubDate'") }}                 as posted_at,
    p ->> 'url'                                             as job_url,
    {{ safe_numeric("p ->> 'salaryMin'") }}                 as salary_min,
    {{ safe_numeric("p ->> 'salaryMax'") }}                 as salary_max,
    nullif(p ->> 'salaryCurrency', '')                      as salary_currency,
    nullif(p ->> 'salaryPeriod', '')                        as salary_period,
    null::text                                              as salary_text,
    {{ json_list_to_text("p -> 'jobLevel'") }}              as seniority_hint,
    {{ json_list_to_text("p -> 'jobType'") }}               as employment_type,
    {{ json_list_to_text("p -> 'jobIndustry'") }}           as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
