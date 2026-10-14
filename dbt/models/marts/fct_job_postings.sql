-- Gold: one row per distinct tech job (after cross-source dedup).
-- Dimensions are kept as descriptive columns for now; Phase 1c splits them out.
with d as (select * from {{ ref('int_postings_deduped') }}),

scope as (
    select
        posting_key,
        bool_or(region = 'Worldwide') as is_worldwide
    from {{ ref('int_posting_geo') }}
    group by 1
)

select
    d.job_id,
    d.job_title,
    d.company_name,
    coalesce(ind.industry, 'Not identified')    as industry,
    d.track,
    d.role_family,
    d.seniority,
    d.work_mode,
    case
        when d.work_mode <> 'Remote' then null
        when coalesce(scope.is_worldwide, false) then 'Worldwide'
        when d.primary_region is not null then 'Restricted'
        else 'Unknown'
    end                                         as remote_scope,
    d.location_text,
    d.geo_restriction_text                      as remote_eligibility_text,
    d.timezone_restriction_text,
    d.primary_country,
    d.primary_region,
    d.salary_min,
    d.salary_max,
    upper(d.salary_currency)                    as salary_currency,
    lower(d.salary_period)                      as salary_period,
    d.salary_text,
    sal.annual_min_usd                          as salary_annual_min_usd,
    sal.annual_max_usd                          as salary_annual_max_usd,
    sal.annual_mid_usd                          as salary_annual_mid_usd,
    sal.annual_mid_eur                          as salary_annual_mid_eur,
    coalesce(sal.salary_is_plausible, false)    as has_comparable_salary,
    d.employment_type,
    coalesce(sig.nationals_only, false)            as nationals_only,
    coalesce(sig.arabic_required, false)           as arabic_required,
    coalesce(sig.offers_visa_or_relocation, false) as offers_visa_or_relocation,
    d.posted_at,
    d.job_first_seen_date                       as first_seen_date,
    d.job_last_seen_date                        as last_seen_date,
    d.job_last_seen_date - d.job_first_seen_date + 1 as days_listed,
    d.job_is_active                             as is_active,
    d.source                                    as primary_source,
    d.listed_on,
    d.listing_count,
    d.job_url,
    d.posting_key                               as primary_posting_key,
    d.description_text
from d
left join scope using (posting_key)
left join {{ ref('int_job_salary') }} sal using (job_id)
left join {{ ref('int_company_industry') }} ind on ind.company_name = d.company_name
left join {{ ref('int_job_signals') }} sig using (job_id)
where d.role_family <> 'Not a tech role'
