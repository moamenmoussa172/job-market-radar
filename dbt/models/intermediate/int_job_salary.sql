-- Salary as one comparable number: annual, in USD and EUR.
--   1. period  -> annual multiplier via seeds/salary_periods.csv
--   2. currency -> EUR via the ECB rate on (or before) the day we first saw
--      the job, then EUR -> USD with that same day's USD rate
--   3. plausibility check: annual USD outside 5k..1.5M is kept but flagged
--      (usually a monthly figure labelled as yearly, or a typo)
-- Jobs with no structured salary are not in this model.
-- The salary comes from the best listing of the job that HAS one: the dedup
-- survivor (e.g. a Greenhouse page) often has no salary while the same job on
-- Himalayas or Ashby does.
with salaried_listings as (
    select distinct on (job_id)
        job_id,
        salary_min,
        salary_max,
        upper(trim(salary_currency))                 as currency,
        lower(trim(salary_period))                   as period
    from {{ ref('int_postings_keyed') }}
    where coalesce(salary_min, salary_max) is not null
      and salary_currency is not null
    order by job_id, source_priority, last_seen_date desc
),

jobs as (
    select
        s.*,
        d.job_first_seen_date                        as first_seen_date
    from salaried_listings s
    join {{ ref('int_postings_deduped') }} d using (job_id)
),

ecb as (
    select rate_date, upper(currency) as currency, units_per_eur
    from {{ source('raw', 'fx_rates') }}
),

-- Gulf currencies (AED, SAR, QAR, ...) are pegged to the US dollar and not in the
-- ECB list: derive their EUR rate from the day's USD rate (seeds/currency_pegs.csv).
rates as (
    select * from ecb
    union all
    select u.rate_date, p.currency, p.units_per_usd * u.units_per_eur
    from ecb u
    cross join {{ ref('currency_pegs') }} p
    where u.currency = 'USD'
      and p.currency not in (select currency from ecb)
),

with_rates as (
    select
        j.*,
        coalesce(p.periods_per_year, 1)               as periods_per_year,
        p.periods_per_year is null                    as period_assumed_annual,
        cur.units_per_eur                             as cur_per_eur,
        usd.units_per_eur                             as usd_per_eur,
        cur.rate_date                                 as fx_rate_date
    from jobs j
    left join {{ ref('salary_periods') }} p
      on p.salary_period = j.period
    left join lateral (
        select r.units_per_eur, r.rate_date
        from rates r
        where r.currency = j.currency
        order by (r.rate_date <= j.first_seen_date) desc, abs(r.rate_date - j.first_seen_date)
        limit 1
    ) cur on true
    left join lateral (
        select r.units_per_eur
        from rates r
        where r.currency = 'USD'
        order by (r.rate_date <= j.first_seen_date) desc, abs(r.rate_date - j.first_seen_date)
        limit 1
    ) usd on true
),

annual as (
    select
        *,
        coalesce(salary_min, salary_max) * periods_per_year   as annual_min_local,
        coalesce(salary_max, salary_min) * periods_per_year   as annual_max_local
    from with_rates
)

select
    job_id,
    currency                                                  as salary_currency_original,
    period                                                    as salary_period_original,
    period_assumed_annual,
    annual_min_local,
    annual_max_local,
    fx_rate_date,
    round(annual_min_local / cur_per_eur, 0)                  as annual_min_eur,
    round(annual_max_local / cur_per_eur, 0)                  as annual_max_eur,
    round(annual_min_local / cur_per_eur * usd_per_eur, 0)    as annual_min_usd,
    round(annual_max_local / cur_per_eur * usd_per_eur, 0)    as annual_max_usd,
    round((annual_min_local + annual_max_local) / 2 / cur_per_eur * usd_per_eur, 0)
                                                              as annual_mid_usd,
    round((annual_min_local + annual_max_local) / 2 / cur_per_eur, 0)
                                                              as annual_mid_eur,
    coalesce(
        (annual_min_local + annual_max_local) / 2 / cur_per_eur * usd_per_eur between 5000 and 1500000,
        false)                                                as salary_is_plausible
from annual
where cur_per_eur is not null   -- currency the ECB doesn't publish -> can't convert
