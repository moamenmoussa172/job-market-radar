-- Location texts that matched no geo pattern. Use this to grow
-- seeds/geo_patterns.csv: the top rows are the next patterns to add.
select
    case when work_mode = 'Remote' then coalesce(geo_restriction_text, location_text)
         else location_text end          as geo_text,
    work_mode,
    count(*)                             as postings,
    string_agg(distinct source, ', ')    as sources
from {{ ref('int_postings_classified') }} p
where not exists (
    select 1 from {{ ref('int_posting_geo') }} g where g.posting_key = p.posting_key
)
group by 1, 2
order by postings desc
