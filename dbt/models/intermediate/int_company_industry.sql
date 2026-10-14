-- Industry of each employer, so tech jobs can be compared across business fields
-- (a data engineer in a bank vs in a startup). First match wins:
--   1. the curated company list (seeds/companies.csv)
--   2. keyword rules on the company name (seeds/industry_keywords.csv, by priority)
--   3. 'Not identified'
with names as (
    select distinct company_name, {{ company_key('company_name') }} as company_key
    from {{ ref('int_postings_deduped') }}
    where company_name is not null
),

listed as (
    select distinct on (company_key) company_key, industry
    from (select {{ company_key('company') }} as company_key, industry from {{ ref('companies') }}) c
    where company_key <> ''
    order by company_key, industry
),

by_keyword as (
    select distinct on (n.company_name) n.company_name, k.industry
    from names n
    join {{ ref('industry_keywords') }} k on n.company_name ~* k.pattern
    order by n.company_name, k.priority
)

select
    n.company_name,
    coalesce(l.industry, kw.industry, 'Not identified')            as industry,
    case when l.industry is not null then 'company list'
         when kw.industry is not null then 'name keywords'
         else 'none' end                                            as industry_source
from names n
left join listed l on l.company_key = n.company_key and n.company_key <> ''
left join by_keyword kw on kw.company_name = n.company_name
