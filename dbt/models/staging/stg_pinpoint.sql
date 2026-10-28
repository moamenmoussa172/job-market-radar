-- Pinpoint careers sites (<company>.pinpointhq.com/postings.json): full descriptions, location,
-- workplace type (remote / hybrid / on-site) and, when the company shares it, the pay range.
with base as ({{ source_snapshots('pinpoint') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ',
            coalesce(nullif(p #>> '{location,city}', ''), nullif(p #>> '{location,name}', '')),
            nullif(p #>> '{location,province}', ''),
            coalesce(nullif(p #>> '{location,country}', ''), nullif(p ->> 'board_country', ''))), '')
                                                                          as loc,
        lower(coalesce(p ->> 'workplace_type', ''))                       as wp
    from base
)

select
    'pinpoint'::text                                        as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    loc                                                     as location_text,
    wp like '%remote%'                                      as is_remote_flag,
    case when wp like '%remote%' then 'remote' when wp like '%hybrid%' then 'hybrid' end as workplace_type,
    case when wp like '%remote%' then loc end               as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    nullif(concat_ws(' ', p ->> 'description', p ->> 'key_responsibilities', p ->> 'skills_knowledge_expertise'), '')
                                                            as description_html,
    {{ safe_timestamp("coalesce(p ->> 'published_at', p ->> 'created_at')") }} as posted_at,
    p ->> 'url'                                             as job_url,
    case when p ->> 'compensation_minimum' ~ '^[0-9.]+$' then (p ->> 'compensation_minimum')::numeric end as salary_min,
    case when p ->> 'compensation_maximum' ~ '^[0-9.]+$' then (p ->> 'compensation_maximum')::numeric end as salary_max,
    nullif(p ->> 'compensation_currency', '')               as salary_currency,
    case lower(coalesce(p ->> 'compensation_frequency', ''))
        when 'year' then 'year' when 'yearly' then 'year' when 'annually' then 'year'
        when 'month' then 'month' when 'monthly' then 'month' when 'hour' then 'hour' when 'hourly' then 'hour'
    end                                                     as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'employment_type', '')                     as employment_type,
    nullif(coalesce(p #>> '{job,department,name}', p #>> '{department,name}'), '') as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
