-- France Travail (France's public employment service) "Offres d'emploi v2" API. Full description in
-- plain text (French), the place as "75 - Paris 8e Arrondissement", the employer is sometimes hidden.
-- Pay comes as text: "Annuel de 45000.00 Euros à 55000.00 Euros sur 12 mois", "Mensuel de 2500.0 Euros ...".
with base as ({{ source_snapshots('francetravail') }}),

pay as (
    select base.*,
        regexp_match(coalesce(p -> 'salaire' ->> 'libelle', ''),
            '^\s*(Annuel|Mensuel|Horaire)\s+de\s+([0-9]+(?:[.,][0-9]+)?)\s*Euros?(?:\s+[àa]\s+([0-9]+(?:[.,][0-9]+)?)\s*Euros?)?', 'i') as m
    from base
)

select
    'francetravail'::text                                   as source,
    source_job_id,
    nullif(trim(p ->> 'intitule'), '')                      as job_title,
    nullif(trim(p -> 'entreprise' ->> 'nom'), '')           as company_name,
    concat_ws(', ',
        nullif(trim(regexp_replace(coalesce(p -> 'lieuTravail' ->> 'libelle', ''), '^\s*[0-9]{2,3}[AB]?\s*-\s*', '')), ''),
        'France')                                           as location_text,
    case when coalesce(p ->> 'intitule', '') || ' ' || coalesce(p ->> 'description', '')
              ~* 't[ée]l[ée]travail\s+(complet|total|100)|full\s+remote|100\s*%\s*(remote|t[ée]l[ée]travail)' then true end
                                                            as is_remote_flag,
    case when coalesce(p ->> 'intitule', '') || ' ' || coalesce(p ->> 'description', '')
              ~* 'hybride|t[ée]l[ée]travail\s+partiel|[0-9]\s*jours?\s+de\s+t[ée]l[ée]travail' then 'hybrid' end
                                                            as workplace_type,
    null::text                                              as geo_restriction_text,
    null::text                                              as timezone_restriction_text,
    nullif(p ->> 'description', '')                         as description_html,
    {{ safe_timestamp("p ->> 'dateCreation'") }}            as posted_at,
    coalesce(nullif(p -> 'origineOffre' ->> 'urlOrigine', ''),
             'https://candidat.francetravail.fr/offres/recherche/detail/' || (p ->> 'id'))
                                                            as job_url,
    replace(m[2], ',', '.')::numeric                        as salary_min,
    coalesce(replace(m[3], ',', '.'), replace(m[2], ',', '.'))::numeric
                                                            as salary_max,
    case when m is not null then 'EUR' end                  as salary_currency,
    case lower(m[1]) when 'annuel' then 'annual' when 'mensuel' then 'monthly' when 'horaire' then 'hourly' end
                                                            as salary_period,
    nullif(p -> 'salaire' ->> 'libelle', '')                as salary_text,
    case p ->> 'experienceExige' when 'D' then 'entry' end  as seniority_hint,
    nullif(p ->> 'typeContratLibelle', '')                  as employment_type,
    nullif(p ->> 'romeLibelle', '')                         as tags_text,
    first_seen_date,
    last_seen_date,
    days_seen
from pay
