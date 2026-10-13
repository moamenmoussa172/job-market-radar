-- SmartRecruiters company boards (posting details). location.country is ISO-2;
-- remote/hybrid are explicit flags; compensation is structured when published.
with base as ({{ source_snapshots('smartrecruiters') }}),

shaped as (
    select
        base.*,
        cc.country as country_name,
        nullif(concat_ws(', ', p -> 'location' ->> 'city', p -> 'location' ->> 'region', cc.country), '') as loc,
        case
            when (p -> 'location' ->> 'hybrid')::boolean then 'hybrid'
            when (p -> 'location' ->> 'remote')::boolean then 'remote'
            when p -> 'location' ? 'remote' then 'onsite'
        end as wp
    from base
    left join {{ ref('country_codes') }} cc
      on cc.code = upper(p -> 'location' ->> 'country')
)

select
    'smartrecruiters'::text                                 as source,
    source_job_id,
    nullif(trim(p ->> 'name'), '')                          as job_title,
    coalesce(nullif(trim(p -> 'company' ->> 'name'), ''), p ->> 'board_token')
                                                            as company_name,
    loc                                                     as location_text,
    case wp when 'remote' then true when 'onsite' then false end
                                                            as is_remote_flag,
    wp                                                      as workplace_type,
    case when wp = 'remote' then loc end                    as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    concat_ws(' ',
        p -> 'jobAd' -> 'sections' -> 'jobDescription' ->> 'text',
        p -> 'jobAd' -> 'sections' -> 'qualifications' ->> 'text',
        p -> 'jobAd' -> 'sections' -> 'additionalInformation' ->> 'text')
                                                            as description_html,
    {{ safe_timestamp("left(p ->> 'releasedDate', 19)") }}  as posted_at,
    coalesce(p ->> 'postingUrl',
             'https://jobs.smartrecruiters.com/' || (p ->> 'board_token') || '/' || (p ->> 'id'))
                                                            as job_url,
    {{ safe_numeric("p -> 'compensation' ->> 'min'") }}     as salary_min,
    {{ safe_numeric("p -> 'compensation' ->> 'max'") }}     as salary_max,
    nullif(p -> 'compensation' ->> 'currency', '')          as salary_currency,
    nullif(lower(p -> 'compensation' ->> 'period'), '')     as salary_period,
    null::text                                              as salary_text,
    nullif(p -> 'experienceLevel' ->> 'name', '')           as seniority_hint,
    nullif(p -> 'typeOfEmployment' ->> 'label', '')         as employment_type,
    nullif(concat_ws(', ', p -> 'department' ->> 'label', p -> 'function' ->> 'label'), '')
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
