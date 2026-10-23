-- Oracle Recruiting Cloud career sites (many Gulf banks, telcos and government-owned companies),
-- read through the site's own job search. The listing has a short description; the country comes
-- as an ISO code (PrimaryLocationCountry), expanded for the geo rules.
with base as ({{ source_snapshots('oracle') }}),

shaped as (
    select
        base.*,
        nullif(p ->> 'PrimaryLocation', '')                     as loc_raw,
        upper(nullif(p ->> 'PrimaryLocationCountry', ''))       as cc_code,
        (select string_agg(x ->> 'Name', '; ') from jsonb_array_elements(
             case when jsonb_typeof(p -> 'secondaryLocations') = 'array' then p -> 'secondaryLocations' else '[]'::jsonb end) x)
                                                                as other_locs
    from base
)

select
    'oracle'::text                                          as source,
    source_job_id,
    nullif(trim(p ->> 'Title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), initcap(split_part(split_part(p ->> 'board_token', '/', 1), '.', 1)))
                                                            as company_name,
    nullif(concat_ws('; ', case when loc_raw ~* coalesce(cc.country, '~') then loc_raw
                                else nullif(concat_ws(', ', loc_raw, cc.country), '') end, other_locs), '')
                                                            as location_text,
    case when coalesce(p ->> 'WorkplaceType', '') ~* 'remote' then true end
                                                            as is_remote_flag,
    case when coalesce(p ->> 'WorkplaceType', '') ~* 'hybrid' then 'hybrid'
         when coalesce(p ->> 'WorkplaceType', '') ~* 'remote' then 'remote'
         when coalesce(p ->> 'WorkplaceType', '') ~* 'on.?site' then 'onsite' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    coalesce(p ->> 'ShortDescriptionStr', p ->> 'ExternalDescriptionStr')
                                                            as description_html,
    {{ safe_timestamp("p ->> 'PostedDate'") }}              as posted_at,
    p ->> 'job_url'                                         as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(concat_ws(', ', p ->> 'JobSchedule', p ->> 'ContractType'), '')
                                                            as employment_type,
    nullif(p ->> 'JobFamily', '')                           as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
left join {{ ref('country_codes') }} cc on cc.code = shaped.cc_code
