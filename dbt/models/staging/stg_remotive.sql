-- Remotive: remote-only board. candidate_required_location = who may apply.
with base as ({{ source_snapshots('remotive') }})

select
    'remotive'::text                                        as source,
    source_job_id,
    nullif(trim(p ->> 'title'), '')                         as job_title,
    nullif(trim(p ->> 'company_name'), '')                  as company_name,
    p ->> 'candidate_required_location'                     as location_text,
    true                                                    as is_remote_flag,
    null::text                                              as workplace_type,
    p ->> 'candidate_required_location'                     as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    p ->> 'description'                                     as description_html,
    {{ safe_timestamp("p ->> 'publication_date'") }}        as posted_at,
    p ->> 'url'                                             as job_url,
    null::numeric                                           as salary_min,
    null::numeric                                           as salary_max,
    null::text                                              as salary_currency,
    null::text                                              as salary_period,
    nullif(p ->> 'salary', '')                              as salary_text,
    null::text                                              as seniority_hint,
    nullif(p ->> 'job_type', '')                            as employment_type,
    {{ json_list_to_text("p -> 'tags'") }}                  as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from base
