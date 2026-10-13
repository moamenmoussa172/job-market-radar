-- Lever company boards. workplaceType is explicit (remote / hybrid / on-site);
-- country is an ISO-2 code, translated to a name via the country_codes seed.
-- The description is spread over description + lists + additional.
with base as ({{ source_snapshots('lever') }}),

shaped as (
    select
        base.*,
        coalesce(
            nullif({{ json_list_to_text("p -> 'categories' -> 'allLocations'") }}, ''),
            p -> 'categories' ->> 'location'
        )                                   as locations,
        cc.country                          as country_name,
        lower(p ->> 'workplaceType')        as wp
    from base
    left join {{ ref('country_codes') }} cc
      on cc.code = upper(p ->> 'country')
)

select
    'lever'::text                                           as source,
    source_job_id,
    nullif(trim(p ->> 'text'), '')                          as job_title,
    initcap(replace(p ->> 'board_token', '-', ' '))         as company_name,
    nullif(concat_ws(', ', locations, country_name), '')    as location_text,
    case wp when 'remote' then true when 'on-site' then false end
                                                            as is_remote_flag,
    case wp when 'remote' then 'remote' when 'hybrid' then 'hybrid' when 'on-site' then 'onsite' end
                                                            as workplace_type,
    case when wp = 'remote' then nullif(concat_ws(', ', locations, country_name), '') end
                                                            as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    concat_ws(' ',
        p ->> 'description',
        (select string_agg(concat_ws(' ', l ->> 'text', l ->> 'content'), ' ')
           from jsonb_array_elements(case when jsonb_typeof(p -> 'lists') = 'array'
                                          then p -> 'lists' else '[]'::jsonb end) as l),
        p ->> 'additional')                                 as description_html,
    {{ safe_timestamp("p ->> 'createdAt'") }}               as posted_at,
    p ->> 'hostedUrl'                                       as job_url,
    {{ safe_numeric("p -> 'salaryRange' ->> 'min'") }}      as salary_min,
    {{ safe_numeric("p -> 'salaryRange' ->> 'max'") }}      as salary_max,
    nullif(p -> 'salaryRange' ->> 'currency', '')           as salary_currency,
    nullif(p -> 'salaryRange' ->> 'interval', '')           as salary_period,
    nullif(p ->> 'salaryDescriptionPlain', '')              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p -> 'categories' ->> 'commitment', '')          as employment_type,
    nullif(concat_ws(', ', p -> 'categories' ->> 'team', p -> 'categories' ->> 'department'), '')
                                                            as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
