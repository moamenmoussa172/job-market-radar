-- Health of the self-expanding company board registry.
-- How many boards per ATS are active / waiting / dead, and how many were
-- discovered automatically vs seeded from company_boards.csv.
select
    ats,
    status,
    origin,
    count(*)                                         as boards,
    coalesce(sum(data_jobs_last_run), 0)             as data_jobs_last_run,
    string_agg(distinct discovered_from, ', ')       as discovered_via,
    max(first_seen_at)::date                         as newest_board_added
from {{ source('raw', 'company_boards') }}
group by 1, 2, 3
order by 1, 2, 3
