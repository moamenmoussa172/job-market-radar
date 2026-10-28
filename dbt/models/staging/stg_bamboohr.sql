-- BambooHR careers sites (<company>.bamboohr.com/careers). The list gives title, department,
-- employment type and location; the description comes from each job's detail page (tech jobs only).
-- locationType: 0 = on-site, 1 = remote, 2 = hybrid (isRemote is set on older boards).
with base as ({{ source_snapshots('bamboohr') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ',
            coalesce(nullif(p #>> '{atsLocation,city}', ''), nullif(p #>> '{location,city}', '')),
            coalesce(nullif(p #>> '{atsLocation,state}', ''), nullif(p #>> '{atsLocation,province}', ''),
                     nullif(p #>> '{location,state}', '')),
            coalesce(nullif(p #>> '{atsLocation,country}', ''), nullif(p ->> 'board_country', ''))), '')
                                                                          as loc,
        (p ->> 'isRemote') = 'true' or (p ->> 'locationType') = '1'      as remote,
        (p ->> 'locationType') = '2'                                     as hybrid
    from base
)

select
    'bamboohr'::text                                        as source,
    source_job_id,
    nullif(trim(p ->> 'jobOpeningName'), '')                as job_title,
    coalesce(nullif(p ->> 'board_company', ''), initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    loc                                                     as location_text,
    remote                                                  as is_remote_flag,
    case when remote then 'remote' when hybrid then 'hybrid' end as workplace_type,
    case when remote then loc end                           as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    nullif(p ->> 'description', '')                         as description_html,
    {{ safe_timestamp("p ->> 'datePosted'") }}              as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    nullif(p ->> 'compensation', '')                        as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'employmentStatusLabel', '')               as employment_type,
    nullif(p ->> 'departmentLabel', '')                     as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
