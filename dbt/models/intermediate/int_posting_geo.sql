-- Posting -> (country, region) bridge, by matching location text against
-- the geo_patterns seed. For remote jobs we match the *eligibility* text
-- (who may apply); for onsite/hybrid we match the office location.
with p as (
    select
        posting_key,
        work_mode,
        case when work_mode = 'Remote'
             then coalesce(geo_restriction_text, location_text)
             else location_text
        end as geo_text
    from {{ ref('int_postings_classified') }}
),

worldwide as (
    select posting_key, null::text as country, 'Worldwide'::text as region
    from p
    where work_mode = 'Remote'
      and (geo_text is null
           or geo_text ~* '\m(anywhere|worldwide|global|international)\M'
           or geo_text ~* '^\s*(remote|fully\s+remote|100%\s+remote)\s*$')
),

matched as (
    select distinct p.posting_key, g.country, g.region
    from p
    join {{ ref('geo_patterns') }} g
      on p.geo_text ~* g.pattern
    where p.posting_key not in (select posting_key from worldwide)
)

select * from worldwide
union all
select * from matched
