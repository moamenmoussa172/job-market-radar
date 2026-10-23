-- SAP SuccessFactors career sites (RSS job feed). The location comes from the job
-- title, e.g. "Data Engineer (Riyadh, SA, 12345)" -> "Riyadh, SA, 12345"; the
-- ISO country code in it is expanded to the country name for the geo rules.
with base as ({{ source_snapshots('successfactors') }}),

shaped as (
    select
        base.*,
        nullif(p ->> 'location', '')                                     as loc_raw,
        (regexp_match(coalesce(p ->> 'location', ''), '(?:^|,\s*)([A-Z]{2})(?:\s*,|\s*$)'))[1] as cc_code,
        regexp_match(coalesce(p ->> 'pubDate', ''),
                     '^[A-Za-z]{3}, (\d{1,2}) ([A-Za-z]{3}) (\d{4}) (\d{2}:\d{2}:\d{2})')     as pub
    from base
)

select
    'successfactors'::text                                  as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    case when p ->> 'board_token' = 'opportunities.vodafone.com' and p ->> 'title' ~* '\m_?vois\M'
         then '_VOIS'                                       -- Vodafone Intelligent Solutions posts on Vodafone's site
         else coalesce(nullif(p ->> 'board_company', ''), (select case when length(t) <= 3 then upper(t) else initcap(t) end
                                                                      from (select split_part(p ->> 'board_token', '.', 2) as t) x))
    end                                                     as company_name,
    nullif(concat_ws(', ', loc_raw, cc.country), '')        as location_text,
    case when loc_raw ~* '\mremote\M' then true end         as is_remote_flag,
    case when loc_raw ~* '\mremote\M' then 'remote' end     as workplace_type,
    case when loc_raw ~* '\mremote\M' then loc_raw end      as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    case when pub[1] is not null                            -- RSS date: "Fri, 16 Oct 2026 09:30:00 GMT"
         then to_timestamp(pub[1] || ' ' || pub[2] || ' ' || pub[3] || ' ' || pub[4], 'DD Mon YYYY HH24:MI:SS')
    end                                                     as posted_at,
    p ->> 'link'                                            as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    null::text                                              as salary_text,
    null::text                                              as seniority_hint,
    null::text                                              as employment_type,
    null::text                                              as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from shaped
left join {{ ref('country_codes') }} cc on cc.code = shaped.cc_code
