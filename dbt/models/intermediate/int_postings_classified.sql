-- Rule-based classification from the title (and source hints).
-- Order of the WHEN branches matters: the first match wins.
-- role_family -> track mapping lives in seeds/role_tracks.csv (joined in int_postings_tracked).
with p as (select * from {{ ref('int_postings_unioned') }}),

classified as (
select
    p.*,

    case
        -- ---------------------------------------------------------------- not tech
        when job_title ~* '(\mwarehouse|\mlager)\s*(associate|lead|operations?|operative|worker|clerk|picker|supervisor|manager|shift|team|employee|mitarbeiter)|schichtleiter|(operations|logistics)\s+manager,?\s+warehouse'
         and job_title !~* 'data|\mdwh\M|\medw\M|\mbi\M|analytics'
            then 'Not a tech role'
        -- business jobs that only mention AI (same rule as is_tech_role in filters.py)
        when job_title ~* '\mai\M|artificial\s+intelligence'
         and job_title ~* 'trainer|strateg|transformation|\mgtm\M|go[\s-]to[\s-]market|market(er|ing)|growth|talent|accelerator|operations|communications|business\s+risk|legal|policy|\msales\M|recruit|adoption|evangelist|writer|tutor|annotat|content'
         and job_title !~* 'engineer|developer|scientist|research|architect|programmer|\mml\M|machine\s+learning|\mdata\M'
            then 'Not a tech role'
        when job_title ~* 'data\s+assistant|medical\s+data|\mai\s+trainers?\M'
            then 'Not a tech role'

        -- ---------------------------------------------------- QA & testing (before any "analyst" rule)
        when job_title ~* '\m(qa|qe|sdet|tester|testeur|testing)\M|quality\s+assurance|test\s*(automation|engineer|analyst|lead|manager|specialist|architect)|testautomat|softwaretest|\mautomation\s+tester'
         and job_title !~* 'data\s+quality|penetration|pen\s*test'
            then case when job_title ~* 'automat|sdet|selenium|cypress|playwright|appium|\mqe\M|software\s+(development\s+)?engineer\s+in\s+test'
                      then 'QA Automation Engineer' else 'QA / Test Engineer' end

        -- ------------------------------------------------- ERP & CRM (SAP, Salesforce, Dynamics, Oracle apps)
        when job_title ~* '\msap\M|\mabap\M|s/4\s*hana|salesforce|\msfdc\M|dynamics\s*365|dynamics\s+(crm|ax|nav)|\md365\M|business\s+central|oracle\s+(e-?business|ebs|fusion|erp|apps|hcm|scm|financials|cloud\s+(erp|hcm|financials))|servicenow|\modoo\M|power\s+(apps|platform|automate)|\m(erp|crm)\s+(developer|consultant|engineer|specialist|analyst|administrator|architect|lead|manager)'
         and job_title !~* 'data\s+(engineer|analyst|scientist)|analytics'
            then case when job_title ~* 'develop|engineer|\mabap\M|\mapex\M|technical|programmer|architect'
                      then 'ERP / CRM Developer' else 'ERP / CRM Consultant' end

        -- --------------------------------------------------------------- Data & AI
        when job_title ~* 'governance|data\s+protection|privacy|datenschutz|data\s+steward|data\s+catalog|\mgdpr\M'
            then 'Data Governance / Privacy'
        when job_title ~* 'analytics\s+engineer'
            then 'Analytics Engineer'
        when job_title ~* '\m(data|etl|elt|big\s+data|data\s+platform|data\s+pipeline|data\s+warehouse|data\s+integration)\s+(engineer|developer|architect)'
          or job_title ~* 'dateningenieur|data-?engineer|ingénieur\s+(de\s+)?données|ingeniero\s+de\s+datos|\metl\M'
          or (job_title ~* '\m(engineer|developer)\M'
              and job_title ~* 'data\s*(platforms?|systems?|infrastructure|ops|pipelines?|factory|extraction|lake|integration)|distributed\s+data|\mdataops\M|data\s*&\s*(ai\s+)?(platforms?|systems?)|data\s*/\s*software|data\s+enablement')
          or job_title ~* 'data\s+(and|&)\s+(ai|analytics)\s+(engineer|architect)'
            then 'Data Engineer'
        when job_title ~* '\mmlops\M|ml\s*ops|machine\s+learning\s+(platform|infrastructure|ops)\s+engineer|\mllmops\M'
            then 'MLOps Engineer'
        when job_title ~* '(research|applied)\s+scientist|\mai\s+researcher|research\s+engineer'
         and job_title !~* 'data\s+scien|clinical|market|ux|user'
            then 'AI Research Scientist / Engineer'
        when job_title ~* 'data\s+scien|\mscientist\M|scientifique\s+des\s+données|científico\s+de\s+datos'
            then 'Data Scientist'
        when job_title ~* 'machine\s+learning|\mml\M|\mmlops\M|deep\s+learning|\mnlp\M|computer\s+vision|\mai\s+(engineer|developer|researcher|architect)|\mllm\M|genai|\mai(\s*/\s*|\s+)(agent|safety|agentic|platform|applied|research)\s+(engineers?|developers?|scientists?)|agent(ic)?\s+(ai\s+)?engineer|ai\s+safety'
            then 'ML / AI Engineer'
        when job_title ~* 'business\s+intelligence|\mbi\M|power\s*bi|tableau|looker|\mreporting\s+(analyst|developer|engineer|specialist)'
            then 'BI Analyst / Developer'

        when job_title ~* '\mdba\M|\mdbre\M|database\s+(administrator|admin|engineer|reliability|specialist|architect)'
            then 'Database Administrator'

        -- --------------------------------------------------------------- Security
        when job_title ~* '\msecurity\M|\mcyber|\msoc\M|penetration|pen\s*test|\mappsec\M|\minfosec\M|\miam\s+(engineer|analyst)|threat|vulnerabilit|\mgrc\M'
            then 'Security Engineer / Analyst'

        -- --------------------------------------------------------------- UI / UX design
        when job_title ~* '(ux|ui|user\s+experience|user\s+interface|product|interaction|visual|web|service|motion)\s*(/\s*(ux|ui)\s*)?(designer|design\s+(lead|manager|director))|\mdesigner\M|design\s+systems?|\mux\s+(research|writer|lead|manager)|\mui\s*/\s*ux|\mux\s*/\s*ui'
            then case when job_title ~* 'research' then 'UX Researcher'
                      when job_title ~* '\mui\M|visual|web\s+designer|motion' and job_title !~* '\mux\M|product' then 'UI / Visual Designer'
                      else 'UX / Product Designer' end

        -- -------------------------------------- analyst roles (data track unless clearly IT)
        when job_title ~* '\m(systems?|it|technical|functional|software|application|erp|sap|crm|salesforce)\s+(business\s+)?analyst'
            then 'Systems / IT Analyst'
        when job_title ~* '(business|product|financial|finance|credit|risk|pricing|venture|clearing|operations|marketing|sales|revenue)\s+analyst'
            then 'Business / Domain Analyst'
        when job_title ~* 'data\s+analy|analytics|analyst|datenanaly|analyste|analista|insights?\s+(analyst|lead|manager|specialist)'
            then 'Data Analyst'

        -- ---------------------------------------------------------- Networks & telecom
        when job_title ~* 'telecom|\mrf\s+(engineer|planning|optimi[sz]ation)|\mran\M|\m(5g|lte|volte)\M|core\s+network|transmission\s+engineer|\mmicrowave\M|\mbss\M|\moss\M|packet\s+core'
            then 'Telecom Engineer'
        when job_title ~* 'network\s+(engineer|administrator|admin|architect|specialist|analyst|operations|support|lead)|\mnoc\M|\mvoip\M|unified\s+communications|wireless\s+engineer|\mccnp\M|\mccie\M|sd-?wan'
            then 'Network Engineer'

        -- --------------------------------------------------------- IT, DevOps & cloud
        when job_title ~* 'it\s+support|help\s*desk|service\s+desk|desktop\s+support|sys(tem)?\s*admin|system\s+administrator|systemadministrat|it\s+(administrator|technician|specialist|engineer)|fachinformatiker'
            then 'IT Support / Systems Admin'
        when job_title ~* '\msre\M|site\s+reliability'
            then 'Site Reliability Engineer'
        when job_title ~* '\m(devops|devsecops|dev\s*ops)\M|platform\s+engineer|release\s+engineer|build\s+engineer|kubernetes|infrastructure\s+engineer'
            then 'DevOps / Platform Engineer'
        when job_title ~* 'cloud\s+(engineer|architect|developer|specialist|consultant)|\m(aws|azure|gcp)\s+(engineer|architect|developer)|infrastructure|systems?\s+engineer'
            then 'Cloud / Infrastructure Engineer'

        -- -------------------------------------------------------- product & delivery
        when job_title ~* 'scrum\s+master|agile\s+coach|delivery\s+enabler|release\s+train\s+engineer'
            then 'Scrum Master / Agile Coach'
        when (job_title ~* '(technical|it|software|digital|engineering|tech|delivery|implementation)\s+(project|program|programme|delivery)\s+(manager|lead)|delivery\s+(manager|lead)|\mpmo\M'
              or (job_title ~* '(project|program|programme)\s+manager' and job_title ~* '\m(it|software|digital|technology|technical|cloud|platform|erp|data|ai)\M'))
         and job_title !~* 'construction|civil|mechanical|electrical|clinical|marketing|events?'
            then 'Technical Project / Program Manager'
        when job_title ~* 'product\s+(manager|owner|lead|director)|produktmanager|product\s+owner|chef\s+de\s+produit|head\s+of\s+product|\mcpo\M'
         and job_title !~* '\m(data|daten|données|datos|analytics|bi|ml|insights?)\M|product\s+(marketing|designer)'
            then 'Product Manager / Owner'
        when job_title ~* 'technical\s+writer|documentation\s+engineer|technical\s+(content|documentation)\s+(writer|specialist)|api\s+writer'
            then 'Technical Writer'

        -- ------------------------------------------------------- Software engineering
        when job_title ~* 'go[\s-]to[\s-]market\s+engineer|\mgtm\s+engineer'
            then 'Solutions / Support Engineer'
        when job_title ~* '(engineering|software|development|technical)\s+(manager|director)|\m(manager|director|head)\M[^,]*,\s*(software\s+)?engineering|director\s+of\s+(software\s+)?engineering|head\s+of\s+(engineering|software|technology|development)|\mcto\M|vp\s+(of\s+)?engineering|chief\s+technology'
            then 'Engineering Leadership'
        when job_title ~* 'blockchain|\mweb3\M|solidity|smart\s+contracts?|\mdefi\M'
            then 'Blockchain Engineer'
        when job_title ~* '\m(ios|android|mobile|flutter|react\s+native|swiftui|kotlin\s+multiplatform|xamarin)\M'
            then 'Mobile Engineer'
        when job_title ~* 'full[\s-]?stack|fullstack'
            then 'Full-Stack Engineer'
        when job_title ~* 'front[\s-]?end|frontend|\mui\s+(engineer|developer)|web\s+(developer|engineer)|javascript|typescript|\mreact\M|angular|\mvue\M|svelte|wordpress|shopify\s+developer'
            then 'Frontend Engineer'
        when job_title ~* 'back[\s-]?end|backend|\mapi\s+(engineer|developer)|\mjava\M|\.net\M|c#|\mgolang\M|\mgo\s+(engineer|developer)|\m(python|node(\.?js)?|php|ruby|rails|rust|scala|elixir|django|laravel|spring)\s+(engineer|developer)'
            then 'Backend Engineer'
        when job_title ~* 'embedded|firmware|\mc\+\+|\mrtos\M'
            then 'Embedded / Firmware Engineer'
        when job_title ~* 'game\s+(developer|engineer|programmer)|unity\s+developer|unreal'
            then 'Game Developer'
        when job_title ~* '(solutions?|sales|pre-?sales|customer|support|integration|implementation|forward\s+deployed)\s+(engineer|architect|consultant)|technical\s+account\s+manager'
         and job_title !~* 'data|analytics'
            then 'Solutions / Support Engineer'
        when (job_title ~* '\m(engineer|developer|programmer|architect|coder|sdet)\M|entwickler|développeu|desarrollador|programador|ingeniero\s+de\s+software|ontwikkelaar|informatiker|software\s+(engineering|development)'
              and job_title !~* '\mdata\M|daten|données|datos')
          or job_title ~* 'software\s+(engineer|developer|engineering)'
            then 'Software Engineer'

        -- --------------------------------------- data-adjacent (only titles with data words)
        when job_title ~* '\m(data|daten|données|datos|analytics|bi|ai|ml|machine\s+learning|insights?|lakehouse|lakebase|edw|dwh|dbt)\M'
            then case
                when job_title ~* 'product\s+(manager|owner|marketing|lead|director|partner)'
                    then 'Data Product Management'
                when job_title ~* 'consultant|consulting|pre-?sales|presales|solutions?\s+(architect|engineer|consultant)|account\s+(executive|manager)|\msales\M|berater|practitioner|customer\s+(delivery|success)'
                    then 'Solutions / Consulting'
                when job_title ~* '\m(manager|director|head|vp|vice\s+president|chief|lead)\M|projektleit|project\s+(manager|lead)'
                    then 'Data Leadership'
                else 'Other data role'
            end

        -- ------------------------------------------------------------ other tech
        when job_title ~* 'product\s+(manager|owner)|produktmanager|chef\s+de\s+produit'
            then 'Product Manager / Owner'
        else 'Other tech role'
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
)

select
    c.*,
    coalesce(rt.track, 'IT & Support') as track
from classified c
left join {{ ref('role_tracks') }} rt using (role_family)
