-- Himalayas: remote-only board. An empty locationRestrictions list means
-- the job is open worldwide; otherwise it lists the eligible countries.
with base as ({{ source_snapshots('himalayas') }})

select
    'himalayas'::text                                       as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    nullif(trim(p ->> 'companyName'), '')                   as company_name,
    coalesce(nullif({{ json_list_to_text("p -> 'locationRestrictions'") }}, ''), 'Worldwide')
                                                            as location_text,
    true                                                    as is_remote_flag,
    null::text                                              as workplace_type,
    coalesce(nullif({{ json_list_to_text("p -> 'locationRestrictions'") }}, ''), 'Worldwide')
                                                            as geo_restriction_text,
    nullif({{ json_list_to_text("p -> 'timezoneRestrictions'") }}, '')
                                                            as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    {{ safe_timestamp("p ->> 'pubDate'") }}                 as posted_at,
    coalesce(p ->> 'applicationLink', p ->> 'guid')         as job_url,
    {{ safe_numeric("p ->> 'minSalary'") }}                 as salary_min,
    {{ safe_numeric("p ->> 'maxSalary'") }}                 as salary_max,
    nullif(p ->> 'currency', '')                            as salary_currency,
    nullif(p ->> 'salaryPeriod', '')                        as salary_period,
    null::text                                              as salary_text,
    {{ json_list_to_text("p -> 'seniority'") }}             as seniority_hint,
    {{ json_list_to_text("p -> 'employmentType'") }}        as employment_type,
    {{ json_list_to_text("p -> 'categories'") }}            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
