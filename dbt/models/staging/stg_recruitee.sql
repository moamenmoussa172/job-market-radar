-- Recruitee company boards (public Careers Site API, /api/offers/).
-- remote / hybrid / on_site are booleans; country_code is ISO-2; salary is an
-- object (min, max, currency, period) that most companies leave empty.
with base as ({{ source_snapshots('recruitee') }}),

shaped as (
    select
        base.*,
        nullif(coalesce(nullif(p ->> 'location', ''),
                        concat_ws(', ', nullif(p ->> 'city', ''), cc.country),
                        p ->> 'board_country'), '')                        as loc,
        case
            when p ->> 'hybrid' = 'true'  then 'hybrid'
            when p ->> 'remote' = 'true'  then 'remote'
            when p ->> 'on_site' = 'true' then 'onsite'
        end                                                                as wp,
        case when jsonb_typeof(p -> 'salary') = 'object' then p -> 'salary' end as salary
    from base
    left join {{ ref('country_codes') }} cc
      on cc.code = upper(p ->> 'country_code')
)

select
    'recruitee'::text                                       as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    coalesce(nullif(p ->> 'board_company', ''), nullif(p ->> 'company_name', ''),
             initcap(replace(p ->> 'board_token', '-', ' ')))
                                                            as company_name,
    loc                                                     as location_text,
    case wp when 'remote' then true when 'onsite' then false end
                                                            as is_remote_flag,
    wp                                                      as workplace_type,
    case when wp = 'remote' then loc end                    as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    concat_ws(' ', p ->> 'description', p ->> 'requirements')
                                                            as description_html,
    coalesce({{ safe_timestamp("replace(p ->> 'published_at', ' UTC', 'Z')") }},
             {{ safe_timestamp("replace(p ->> 'created_at', ' UTC', 'Z')") }})
                                                            as posted_at,
    coalesce(p ->> 'careers_url', p ->> 'careers_apply_url')
                                                            as job_url,
    {{ safe_numeric("salary ->> 'min'") }}                  as salary_min,
    {{ safe_numeric("salary ->> 'max'") }}                  as salary_max,
    nullif(salary ->> 'currency', '')                       as salary_currency,
    nullif(salary ->> 'period', '')                         as salary_period,
    null::text                                              as salary_text,
    nullif(coalesce(p ->> 'experience_code', p ->> 'experience'), '')
                                                            as seniority_hint,
    nullif(coalesce(p ->> 'employment_type_code', p ->> 'employment_type'), '')
                                                            as employment_type,
    nullif(p ->> 'department', '')                          as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
