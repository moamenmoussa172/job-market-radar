-- Ashby company boards. workplaceType is explicit (OnSite / Remote / Hybrid);
-- salary comes from compensation.summaryComponents (compensationType = Salary).
with base as ({{ source_snapshots('ashby') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ',
            p ->> 'location',
            p -> 'address' -> 'postalAddress' ->> 'addressCountry',
            (select string_agg(concat_ws(', ', s ->> 'location', s -> 'address' ->> 'addressCountry'), ', ')
               from jsonb_array_elements(case when jsonb_typeof(p -> 'secondaryLocations') = 'array'
                                              then p -> 'secondaryLocations' else '[]'::jsonb end) as s)
        ), '')                                                   as locations,
        case
            when lower(p ->> 'workplaceType') = 'remote' or (p ->> 'isRemote')::boolean then 'remote'
            when lower(p ->> 'workplaceType') = 'hybrid' then 'hybrid'
            when lower(p ->> 'workplaceType') = 'onsite' then 'onsite'
        end                                                      as wp,
        (select c
           from jsonb_array_elements(
                    case when jsonb_typeof(p -> 'compensation' -> 'summaryComponents') = 'array'
                         then p -> 'compensation' -> 'summaryComponents' else '[]'::jsonb end) as c
          where c ->> 'compensationType' ilike 'salary'
          limit 1)                                               as salary
    from base
)

select
    'ashby'::text                                           as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    locations                                               as location_text,
    case wp when 'remote' then true when 'onsite' then false end
                                                            as is_remote_flag,
    wp                                                      as workplace_type,
    case when wp = 'remote' then locations end              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    coalesce(p ->> 'descriptionHtml', p ->> 'descriptionPlain')
                                                            as description_html,
    {{ safe_timestamp("p ->> 'publishedAt'") }}             as posted_at,
    coalesce(p ->> 'jobUrl', p ->> 'applyUrl')              as job_url,
    {{ safe_numeric("salary ->> 'minValue'") }}             as salary_min,
    {{ safe_numeric("salary ->> 'maxValue'") }}             as salary_max,
    nullif(salary ->> 'currencyCode', '')                   as salary_currency,
    nullif(salary ->> 'interval', '')                       as salary_period,
    nullif(p -> 'compensation' ->> 'scrapeableCompensationSalarySummary', '')
                                                            as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'employmentType', '')                      as employment_type,
    nullif(concat_ws(', ', p ->> 'department', p ->> 'team'), '')
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
