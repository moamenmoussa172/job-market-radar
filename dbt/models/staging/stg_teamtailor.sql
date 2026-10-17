-- Teamtailor careers sites (<company>.teamtailor.com/jobs.rss). Full HTML description,
-- locations ("City, Country" each), department and remote status ("none" | "hybrid" | "fully").
with base as ({{ source_snapshots('teamtailor') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws('; ',
            (select string_agg(l #>> '{}', '; ')
               from jsonb_array_elements(case when jsonb_typeof(p -> 'locations') = 'array'
                                              then p -> 'locations' else '[]'::jsonb end) as l),
            case when coalesce(jsonb_array_length(case when jsonb_typeof(p -> 'locations') = 'array'
                                                       then p -> 'locations' end), 0) = 0
                 then nullif(p ->> 'board_country', '') end), '')            as loc,
        lower(coalesce(p ->> 'remoteStatus', p ->> 'remote', ''))            as remote_status,
        regexp_match(coalesce(p ->> 'pubDate', ''),
                     '^[A-Za-z]{3}, (\d{1,2}) ([A-Za-z]{3}) (\d{4}) (\d{2}:\d{2}:\d{2})') as pub
    from base
)

select
    'teamtailor'::text                                      as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    loc                                                     as location_text,
    case when remote_status in ('fully', 'remote', 'true') then true
         when remote_status in ('none', 'false') then false end
                                                            as is_remote_flag,
    case when remote_status in ('fully', 'remote', 'true') then 'remote'
         when remote_status = 'hybrid' then 'hybrid'
         when remote_status = 'none' then 'onsite' end      as workplace_type,
    case when remote_status in ('fully', 'remote', 'true') then loc end
                                                            as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    case when pub[1] is not null
         then to_timestamp(pub[1] || ' ' || pub[2] || ' ' || pub[3] || ' ' || pub[4], 'DD Mon YYYY HH24:MI:SS')
    end                                                     as posted_at,
    p ->> 'link'                                            as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    null::text                                              as employment_type,
    nullif(concat_ws(', ', p ->> 'department', p ->> 'role'), '')
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
