-- Adzuna search API (UK, EU, India, South Africa, Singapore, Brazil, Mexico, US, Canada, Australia, NZ). Descriptions are ~500-character snippets.
-- Adzuna fills in *predicted* salaries when a job has none (salary_is_predicted = 1);
-- only real, published salaries are kept. Currency follows the searched country.
with base as ({{ source_snapshots('adzuna') }}),

shaped as (
    select
        base.*,
        nullif(p -> 'location' ->> 'display_name', '')                    as loc,
        coalesce(p ->> 'salary_is_predicted', '0') = '0'                   as real_salary,
        case lower(p ->> 'search_country')
            when 'gb' then 'GBP' when 'pl' then 'PLN' when 'ch' then 'CHF'
            when 'in' then 'INR' when 'za' then 'ZAR' when 'sg' then 'SGD' when 'br' then 'BRL'
            when 'mx' then 'MXN' when 'us' then 'USD' when 'ca' then 'CAD' when 'au' then 'AUD'
            when 'nz' then 'NZD' else 'EUR'
        end                                                                as currency,
        cc.country                                                         as country_name
    from base
    left join {{ ref('country_codes') }} cc
      on cc.code = upper(p ->> 'search_country')
)

select
    'adzuna'::text                                          as source,
    source_job_id,
    nullif(trim(regexp_replace(p ->> 'title', '<[^>]*>', '', 'g')), '')
                                                            as job_title,
    nullif(trim(p -> 'company' ->> 'display_name'), '')     as company_name,
    case when loc ~* coalesce(country_name, '~') then loc
         else nullif(concat_ws(', ', loc, country_name), '') end
                                                            as location_text,
    case when p ->> 'title' ~* 'remote' or p ->> 'description' ~* 'fully remote|100% remote' then true end
                                                            as is_remote_flag,
    case when p ->> 'title' ~* 'hybrid' then 'hybrid'
         when p ->> 'title' ~* 'remote' then 'remote' end   as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    {{ safe_timestamp("p ->> 'created'") }}                 as posted_at,
    p ->> 'redirect_url'                                    as job_url,
    case when real_salary then {{ safe_numeric("p ->> 'salary_min'") }} end
                                                            as salary_min,
    case when real_salary then {{ safe_numeric("p ->> 'salary_max'") }} end
                                                            as salary_max,
    case when real_salary and p ->> 'salary_min' is not null then currency end
                                                            as salary_currency,
    case when real_salary and p ->> 'salary_min' is not null then 'annual' end
                                                            as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(concat_ws(', ', p ->> 'contract_time', p ->> 'contract_type'), '')
                                                            as employment_type,
    nullif(p -> 'category' ->> 'label', '')                 as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
