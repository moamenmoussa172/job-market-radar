-- Rule-based classification from the title (and source hints).
-- Order of the WHEN branches matters: the first match wins.
with p as (select * from {{ ref('int_postings_unioned') }})

select
    p.*,

    case
        -- Physical warehouse / logistics jobs that slipped in via the word "warehouse"
        when job_title ~* '(\mwarehouse|\mlager)\s*(associate|lead|operations?|operative|worker|clerk|picker|supervisor|manager|shift|team)|schichtleiter|(operations|logistics)\s+manager,?\s+warehouse'
         and job_title !~* 'data|\mdwh\M|\medw\M|\mbi\M|analytics'
            then 'Not a data role'

        when job_title ~* 'governance|data\s+protection|privacy|datenschutz|data\s+steward|data\s+catalog|\mgdpr\M'
            then 'Data Governance / Privacy'

        -- Roles named by their craft come first: a "Lead Data Engineer" is a Data Engineer
        when job_title ~* 'analytics\s+engineer'
            then 'Analytics Engineer'
        when job_title ~* '\m(data|etl|elt|big\s+data|data\s+platform|data\s+pipeline|data\s+warehouse|data\s+integration)\s+(engineer|developer|architect)'
          or job_title ~* 'dateningenieur|data-?engineer|ingénieur\s+(de\s+)?données|ingeniero\s+de\s+datos|\metl\M'
          -- software / platform engineers who build data systems
          or (job_title ~* '\m(engineer|developer)\M'
              and job_title ~* 'data\s*(platforms?|systems?|infrastructure|ops|pipelines?|factory|extraction|lake|integration)|distributed\s+data|\mdataops\M|data\s*&\s*(ai\s+)?(platforms?|systems?)|data\s*/\s*software')
            then 'Data Engineer'
        when job_title ~* 'scien'
            then 'Data Scientist'
        when job_title ~* 'machine\s+learning|\mml\M|\mmlops\M|deep\s+learning|\mnlp\M|computer\s+vision|\mai\s+engineer'
            then 'ML / AI Engineer'
        when job_title ~* 'business\s+intelligence|\mbi\M|power\s*bi|tableau|looker|reporting'
            then 'BI Analyst / Developer'
        when job_title ~* '(business|product|financial|finance|credit|risk|pricing|venture|clearing|operations|marketing|sales)\s+analyst'
            then 'Business / Domain Analyst'
        when job_title ~* 'data\s+analy|analytics|analyst|datenanaly|analyste|analista|insights?\s+(analyst|lead|manager|specialist)'
            then 'Data Analyst'

        -- Data-adjacent functions
        when job_title ~* 'product\s+(manager|owner|marketing|lead|director)'
            then 'Data Product Management'
        when job_title ~* 'consultant|consulting|pre-?sales|presales|solutions?\s+(architect|engineer|consultant)|account\s+(executive|manager)|\msales\M|berater|practitioner|customer\s+(delivery|success)'
            then 'Solutions / Consulting'
        when job_title ~* '\m(manager|director|head|vp|vice\s+president|chief|lead)\M|projektleit|project\s+(manager|lead)'
            then 'Data Leadership'

        when job_title ~* 'data|daten|données|datos|lakehouse|lakebase|\medw\M|\mdwh\M'
            then 'Other data role'
        else 'Other'
    end as role_family,

    case
        when job_title ~* '\m(intern|internship|werkstudent\w*|working\s+student|praktikant\w*|praktikum|stage|trainee|apprentice\w*|alternance|student)\M'
            then 'Intern / Student'
        when job_title ~* '\m(junior|jr|entry|graduate|grad)\M'
            then 'Junior'
        when job_title ~* '\m(head|director|vp|vice\s+president|chief)\M'
            then 'Head / Director'
        when job_title ~* '\m(lead|principal|staff|architect|manager)\M'
            then 'Lead / Principal'
        when job_title ~* '\m(senior|sr|snr)\M'
            then 'Senior'
        when seniority_hint ~* 'intern'                    then 'Intern / Student'
        when seniority_hint ~* 'entry|junior'              then 'Junior'
        when seniority_hint ~* 'director|executive|head'   then 'Head / Director'
        when seniority_hint ~* 'lead|principal|staff|manager' then 'Lead / Principal'
        when seniority_hint ~* 'senior'                    then 'Senior'
        when seniority_hint ~* 'mid|middle|intermediate'   then 'Mid'
        else 'Not stated'
    end as seniority,

    case
        -- sources that state it explicitly (Lever, Ashby, Arbeitnow's remote flag) win
        when workplace_type = 'hybrid' then 'Hybrid'
        when workplace_type = 'remote' then 'Remote'
        when workplace_type = 'onsite' then 'Onsite'
        when location_text ~* 'hybrid|hybride' or job_title ~* 'hybrid'
            then 'Hybrid'
        when is_remote_flag
          or source in ('remotive', 'jobicy', 'himalayas')
          or location_text ~* 'remote|home\s*office|anywhere|worldwide|télétravail|teletrabajo|fully\s+distributed'
            then 'Remote'
        else 'Onsite'
    end as work_mode

from p
