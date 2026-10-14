-- Where jobs were originally posted, for the aggregator sources
-- (JSearch: LinkedIn, Indeed, Glassdoor, Bayt, company sites, ...; Jooble: its partner sites).
select
    case k.source
        when 'jsearch' then coalesce(k.tags_text, 'Unknown')
        when 'adzuna'  then 'Adzuna'
        else 'Jooble partner: ' || coalesce(k.tags_text, 'unknown')
    end                                                                     as original_board,
    k.source                                                                as via,
    f.primary_country                                                       as country,
    f.track,
    f.role_family,
    f.work_mode,
    count(distinct f.job_id)                                                as jobs
from {{ ref('int_postings_keyed') }} k
join {{ ref('fct_job_postings') }} f using (job_id)
where k.source in ('jsearch', 'jooble', 'adzuna')
  and f.is_active
group by 1, 2, 3, 4, 5, 6
