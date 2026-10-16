-- Bundesagentur für Arbeit (Germany) job search API. The search result has no
-- description, so skills can't be read for these jobs. Places are German
-- ("Deutschland"); the country is added in English for the geo rules.
with base as ({{ source_snapshots('bundesagentur') }}),

shaped as (
    select
        base.*,
        nullif(concat_ws(', ',
            nullif(p -> 'arbeitsort' ->> 'ort', ''),
            nullif(p -> 'arbeitsort' ->> 'region', ''),
            case when coalesce(p -> 'arbeitsort' ->> 'land', 'Deutschland') ~* 'deutschland' then 'Germany'
                 else p -> 'arbeitsort' ->> 'land' end), '')                as loc
    from base
)

select
    'bundesagentur'::text                                   as source,
    source_job_id,
    nullif(trim(coalesce(p ->> 'titel', p ->> 'beruf')), '') as job_title,
    nullif(trim(p ->> 'arbeitgeber'), '')                   as company_name,
    loc                                                     as location_text,
    case when coalesce(p ->> 'titel', '') ~* 'remote|homeoffice|home office' then true end
                                                            as is_remote_flag,
    case when coalesce(p ->> 'titel', '') ~* 'hybrid' then 'hybrid' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    null::text                                              as description_html,
    {{ safe_timestamp("p ->> 'aktuelleVeroeffentlichungsdatum'") }}
                                                            as posted_at,
    coalesce(nullif(p ->> 'externeUrl', ''),
             'https://www.arbeitsagentur.de/jobsuche/jobdetail/' || (p ->> 'refnr'))
                                                            as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    null::text                                              as employment_type,
    nullif(p ->> 'beruf', '')                               as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
