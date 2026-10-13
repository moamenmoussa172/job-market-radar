{#- One row per job of a source: the latest payload plus its lifecycle
    (first/last day we saw it, and on how many daily snapshots). -#}
{% macro source_snapshots(source_name) -%}
with snaps as (
    select source_job_id, snapshot_date, payload
    from {{ source('raw', 'job_posting_snapshots') }}
    where source = '{{ source_name }}'
),

lifecycle as (
    select
        source_job_id,
        min(snapshot_date) as first_seen_date,
        max(snapshot_date) as last_seen_date,
        count(*)           as days_seen
    from snaps
    group by 1
),

latest as (
    select distinct on (source_job_id) source_job_id, payload
    from snaps
    order by source_job_id, snapshot_date desc
)

select
    latest.source_job_id,
    latest.payload as p,
    lifecycle.first_seen_date,
    lifecycle.last_seen_date,
    lifecycle.days_seen
from latest
join lifecycle using (source_job_id)
{%- endmacro %}
