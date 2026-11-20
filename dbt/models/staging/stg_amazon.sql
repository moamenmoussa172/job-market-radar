-- Amazon's own career site (amazon.jobs), searched country by country.
-- posted_date looks like "November 14, 2026"; the description comes with the qualification lists.
with base as ({{ source_snapshots('amazon') }})

select
    'amazon'::text                                          as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    -- one company, whatever legal entity posts the job ("Amazon Data Services Sweden AB" -> Amazon)
    case when coalesce(p ->> 'company_name', '') ~* '(amazon web services|\maws\M)' then 'Amazon Web Services'
         else 'Amazon' end                                  as company_name,
    -- the country comes from the job's own country code (checked when it was read), never from the search
    case when nullif(p ->> 'country_name', '') is not null
         then concat_ws(', ', nullif(p ->> 'city', ''), p ->> 'country_name') end
                                                            as location_text,
    case when concat(p ->> 'location', ' ', p ->> 'title') ~* '\m(virtual|remote)\M' then true end
                                                            as is_remote_flag,
    case when concat(p ->> 'location', ' ', p ->> 'title') ~* '\m(virtual|remote)\M' then 'remote' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    nullif(concat_ws('<br/>', p ->> 'description', p ->> 'basic_qualifications', p ->> 'preferred_qualifications'), '')
                                                            as description_html,
    case when trim(p ->> 'posted_date') ~ '^[A-Za-z]+ \d{1,2}, \d{4}$'
         then to_date(trim(p ->> 'posted_date'), 'FMMonth FMDD, YYYY')::timestamp end
                                                            as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'job_schedule_type', '')                   as employment_type,
    concat_ws(', ', nullif(p ->> 'job_category', ''), nullif(p ->> 'business_category', ''))
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
