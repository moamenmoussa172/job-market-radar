-- Every listing gets a job_id: normalized company + title + work mode + primary
-- country. Listings that share a job_id are the same job on different boards.
-- Jobs in excluded locations (geo_patterns rows labelled 'Excluded') are dropped from the
-- whole project: they never reach the site, the dashboard, trends or reports.
with excluded as (
    select distinct posting_key from {{ ref('int_posting_geo') }} where country = 'Excluded'
),

p as (
    select * from {{ ref('int_postings_classified') }}
    where posting_key not in (select posting_key from excluded)
),

geo as (
    select
        posting_key,
        min(country) as primary_country,
        min(region)  as primary_region
    from {{ ref('int_posting_geo') }}
    group by 1
),

keyed as (
    select
        p.*,
        geo.primary_country,
        geo.primary_region,
        md5(
            regexp_replace(
                regexp_replace(lower(coalesce(company_name, '')),
                    '\m(gmbh|ag|inc|ltd|llc|se|bv|b\.v\.|sas|sa|plc|corp|corporation|co|company|group)\M', '', 'g'),
                '[^a-z0-9]', '', 'g')
            || '|' ||
            regexp_replace(
                regexp_replace(lower(job_title),
                    '\(\s*(all\s+genders?|[mwfdxh](\s*[/|,]\s*[mwfdxh]+)+)\s*\)', '', 'g'),
                '[^a-z0-9]', '', 'g')
            || '|' || work_mode
            || '|' || coalesce(geo.primary_country, '')
        ) as job_id,
        case source
            when 'greenhouse' then 1   -- company boards: full description, direct company link
            when 'lever'      then 1
            when 'ashby'      then 1
            when 'smartrecruiters' then 1
            when 'workable'   then 1
            when 'recruitee'  then 1
            when 'personio'   then 1
            when 'workday'    then 1
            when 'teamtailor' then 1
            when 'breezy'     then 5   -- no description
            when 'successfactors' then 1
            when 'phenom'     then 2   -- company site, teaser only
            when 'oracle'     then 2   -- company site, short description
            when 'himalayas'  then 2   -- structured eligibility + salary
            when 'jobicy'     then 3
            when 'remoteok'   then 3
            when 'arbeitnow'  then 4
            when 'jsearch'    then 4   -- full description, original board in tags_text
            when 'jooble'     then 6   -- snippet only
            when 'adzuna'     then 6   -- snippet only
            when 'bundesagentur' then 7  -- no description at all
            else 5
        end as source_priority
    from p
    left join geo using (posting_key)
)

select * from keyed
