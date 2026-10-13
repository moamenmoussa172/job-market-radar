-- Where each job is located (onsite/hybrid) or who may apply (remote).
-- One row per job x (country, region). country is NULL for region-level
-- matches like "EMEA" or "Worldwide".
select distinct
    f.job_id,
    g.country,
    g.region
from {{ ref('fct_job_postings') }} f
join {{ ref('int_posting_geo') }} g
  on g.posting_key = f.primary_posting_key
