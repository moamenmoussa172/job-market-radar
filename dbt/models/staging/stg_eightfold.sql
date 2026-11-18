-- Eightfold career sites (Microsoft, Netflix, ...), read through the site's own public job search.
-- Locations are "City, State, Country"; the search list usually has no description (skills come from the title).
with base as ({{ source_snapshots('eightfold') }})

select
    'eightfold'::text                                       as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), nullif(p ->> 'company', ''))
                                                            as company_name,
    nullif(array_to_string(array(select jsonb_array_elements_text(coalesce(p -> 'locations', '[]'::jsonb)) limit 3), ' / '), '')
                                                            as location_text,
    case when lower(coalesce(p ->> 'work_location_option', '')) like '%remote%' then true end
                                                            as is_remote_flag,
    case when lower(coalesce(p ->> 'work_location_option', '')) like '%hybrid%' then 'hybrid'
         when lower(coalesce(p ->> 'work_location_option', '')) like '%remote%' then 'remote'
         when lower(coalesce(p ->> 'work_location_option', '')) like '%onsite%' then 'onsite' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    nullif(p ->> 'description', '')                         as description_html,
    case when (p ->> 'posted_ts') ~ '^\d{9,10}$' then to_timestamp((p ->> 'posted_ts')::bigint)::timestamp
         when (p ->> 'posted_ts') ~ '^\d{12,13}$' then to_timestamp((p ->> 'posted_ts')::bigint / 1000)::timestamp
    end                                                     as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    null::text                                              as employment_type,
    nullif(p ->> 'department', '')                          as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
