"""Decides whether a job title belongs to the job families we track.

The raw layer is scoped: we only land tech postings (data, software, QA,
UI/UX design, DevOps/cloud, security, IT) so the daily snapshots stay a
manageable size. Fine-grained classification (track and role family) happens
later in dbt, where it can be re-run over history.

Patterns cover English plus common German / French / Spanish / Dutch terms.
"""
import re

# --------------------------------------------------------------------- data roles
_DATA_INCLUDE = re.compile(
    r"""
    \bdata\b | \banalytics?\b | \banalyst\b | \bbusiness\ intelligence\b | \bbi\b
    | \betl\b | \belt\b | \bdbt\b | \bwarehous | \blakehouse\b | \bbig\ data\b | \bdwh\b | \bedw\b
    | daten | donn[ée]es | \bdatos\b | \bdata-
    | \bmachine\ learning\b | \bml\b | \bmlops\b | \bai\b | scientist
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Titles that mention "data" but are not data-profession roles.
_DATA_EXCLUDE = re.compile(
    r"data\s*entry|data\s*cent(er|re)|datacenter|rechenzentrum|data\s*protection\s*officer"
    r"|data\s+assistant|medical\s+data|\bai\s+trainers?\b",
    re.IGNORECASE,
)

# Physical warehouse / logistics jobs ("Warehouse Associate", "Lager...").
# Only dropped when the title has no data word, so "Data Warehouse Lead" stays.
_WAREHOUSE_NOISE = re.compile(
    r"\b(warehouse|lager)\s*(associate|lead|operations?|operative|worker|clerk|picker|"
    r"supervisor|manager|shift|team|employee|mitarbeiter)|schichtleiter|(operations|logistics)\s+manager,?\s+warehouse",
    re.IGNORECASE,
)
# Business jobs that only mention AI ("AI Strategist", "AI Trainer", "Growth Marketer - x.ai").
# Dropped unless the title also has an engineering / science / data word.
_AI_WORD = re.compile(r"\bai\b|artificial\s+intelligence", re.IGNORECASE)
_AI_NON_TECH = re.compile(
    r"trainer|strateg|transformation|\bgtm\b|go[\s-]to[\s-]market|market(er|ing)|growth|talent|accelerator"
    r"|operations|communications|business\s+risk|legal|policy|\bsales\b|recruit|adoption|evangelist"
    r"|writer|tutor|annotat|content",
    re.IGNORECASE,
)
_AI_ROLE_WORD = re.compile(
    r"engineer|developer|scientist|research|architect|programmer|\bml\b|machine\s+learning|\bdata\b",
    re.IGNORECASE,
)
_DATA_WORD = re.compile(r"data|\bdwh\b|\bedw\b|\bbi\b|analytics", re.IGNORECASE)

# --------------------------------------------------------------- other tech roles
_TECH_INCLUDE = re.compile(
    r"""
    # software engineering, any language / layer
    \b(software|application|frontend|front[\s-]?end|backend|back[\s-]?end|full[\s-]?stack|web|mobile
       |ios|android|flutter|react|angular|vue|node(\.?js)?|javascript|typescript|java|python|golang|go
       |\.net|c\#|c\+\+|php|ruby|rails|rust|kotlin|swift|scala|elixir|embedded|firmware|game|api
       |platform|systems?|cloud|devops|devsecops|site\ reliability|infrastructure|security|cyber
       |network|it|qa|test|automation|integration|solutions?|salesforce|sap)\b
       .{0,40}\b(engineer|developer|dev|programmer|architect|sdet|tester|specialist|administrator|lead|intern)
    | \b(engineer|developer|programmer|architect)\b.{0,30}\b(software|frontend|backend|full[\s-]?stack|mobile
       |ios|android|web|java|python|react|node|\.net|golang|cloud|devops|platform|qa|test)\b
    | \.net\b | (?<!\w)c\# | (?<!\w)c\+\+    # no word boundary before "." or after "#"/"+"
    | \bsoftware\b | \bdevops\b | \bsre\b | site\ reliability | \bsdet\b | \bqa\b | quality\ assurance
    | \btester\b | test\ (automation|engineer|analyst|lead|manager) | \bpenetration | \bpentest | \bsoc\ analyst
    | \bcyber\s*security\b | \binfosec\b | \bappsec\b
    | \b(ux|ui|user\ experience|user\ interface)\b | (product|interaction|visual|web|ui|ux)\s*/?\s*(ux\s*)?designer
    | ux\ research | design\ systems?\b
    | \b(it\ support|help\s?desk|service\ desk|sys(tem)?\s*admin|system\ administrator|network\ (engineer|administrator))\b
    | \b(cto|vp\ (of\ )?engineering|head\ of\ engineering|engineering\ manager)\b
    | scrum\ master | agile\ coach
    # ERP & CRM platforms
    | \bsap\b | \babap\b | s/4\s*hana | salesforce | \bsfdc\b | dynamics\s*365 | dynamics\ (crm|ax|nav) | \bd365\b
    | business\ central | oracle\ (e-?business|ebs|fusion|erp|apps|hcm|scm|financials|cloud|apex|dba|database)
    | servicenow | \bodoo\b | power\ (apps|platform|automate) | \b(erp|crm)\ (developer|consultant|engineer|specialist|analyst|administrator|architect)
    # networks & telecom, databases
    | network\ (engineer|administrator|admin|architect|specialist|operations|support) | \bnoc\b | telecom | \brf\ (engineer|planning|optimi)
    | \bran\ engineer | core\ network | \b(5g|lte)\b | \bvoip\b | sd-?wan | \bccn[ap]\b | \bccie\b
    | \bdba\b | database\ (administrator|admin|engineer|reliability|architect)
    # product & delivery, docs, web3
    | product\ (manager|owner) | produktmanager | \bpmo\b | delivery\ manager
    | (technical|it|software|digital|engineering|tech|implementation)\ (project|program|programme)\ manager
    | technical\ writer | documentation\ engineer | blockchain | \bweb3\b | solidity | smart\ contract
    # mobile, RPA / low-code, GIS, robotics, games & XR
    | \bios\b | \bandroid\b | flutter | native\ (mobile|app) | react[\s-]native | xamarin | objective[\s-]?c | swiftui | jetpack\ compose
    | \brpa\b | uipath | blue\s*prism | automation\ anywhere | outsystems | mendix | \bappian\b | \bpega\b | low[\s-]?code
    | \bgis\b | arcgis | geospatial | robotics?\ (software\ )?(engineer|developer|programmer) | \bros2?\b | \bunity\ (developer|engineer) | \bunreal\b
    | \b(ar|vr|xr)\s*/?\s*(vr|ar)?\ (developer|engineer) | augmented\ reality | virtual\ reality | game\ (developer|programmer|engineer)
    # embedded, automotive & chip design (big in Egypt: Valeo, Siemens EDA, Synopsys, Si-Vision)
    | \basic\b | \bfpga\b | \brtl\b | \bvlsi\b | \buvm\b | systemverilog | design\ verification | verification\ engineer
    | physical\ design | \bdft\b | design[\s-]for[\s-]test | analog\ (layout|design|ic|mixed) | mixed[\s-]signal
    | (pre|post)[\s-]silicon | silicon\ (validation|design|engineer) | chip\ design | static\ timing
    | autosar | automotive\ (software|embedded) | \badas\b | \becu\b | functional\ safety | iso\s*26262 | infotainment | simulink
    # security specialisms, pre-sales, architects, integration, devrel, quant, IT leadership
    | \bsoc\ (analyst|engineer|lead|manager) | security\ (analyst|engineer|architect|consultant|operations) | (information|it|cyber)\ security\ (officer|specialist|manager)
    | incident\ response | threat\ (hunt|intel|detection) | \bdfir\b | ethical\ hack | red\ team | \bgrc\b
    | it\ audit | \bciso\b | iso\s*27001 | identity\ (and|&)\ access | \biam\ (engineer|analyst|specialist|architect|consultant)
    | pre-?sales | sales\ engineer | solutions?\ (consultant|architect|engineer) | enterprise\ architect | technical\ architect
    | integration\ (engineer|developer|specialist|architect) | middleware | mulesoft | \btibco\b | \bboomi\b
    | developer\ (advocate|relations|evangelist) | \bdevrel\b | quant(itative)?\ (developer|analyst|researcher|engineer)
    | performance\ test | load\ test | \bjmeter\b | ux\ writ | content\ designer | conversation(al)?\ designer
    | \bit\ (manager|director|lead|head) | head\ of\ (it|information\ technology|technology|infrastructure) | \bcio\b
    | speech\ (recognition|engineer|scientist|technolog) | (technical|customer|product|application)\ support\ engineer
    | computer\ vision | \bnlp\b | natural\ language | \bllm\b | genai | generative\ ai | prompt\ engineer
    # German / French / Spanish / Dutch
    | entwickler | softwareentwickl | informatiker | fachinformatiker | systemadministrat | testautomat
    | d[ée]veloppeu | ing[ée]nieur\ (logiciel|devops|cloud|qa|test) | testeur
    | desarrollador | programador | ingenier[oa]\ de\ (software|sistemas|qa) | ontwikkelaar
    """,
    re.IGNORECASE | re.VERBOSE,
)

# "Engineer"/"designer"/"technician" jobs outside software. Dropped unless the
# title also has a clear software word (e.g. "Embedded Software Engineer, Automotive").
_NON_TECH = re.compile(
    r"""
    \b(mechanical|civil|electrical|electronics?|chemical|structural|process|manufacturing|production
       |hvac|construction|maintenance|field\ service|service\ technician|mechatronic|aerospace|nuclear
       |biomedical|petroleum|mining|environmental|geotechnical|piping|welding|cnc|plant|facilities
       |fashion|interior|landscape|furniture|jewel\w*|textile|kitchen|floral|instructional|packaging
       |graphic|print|garden|hair|nail|tattoo|lighting|sound|stage|costume|set)\b
    | \b(sales|account)\s+(manager|executive|representative)\b | \bdriver\b | \bnurse\b | \bmedical\b
    | test\s+driver | crash\s+test | clinical | laborator
    """,
    re.IGNORECASE | re.VERBOSE,
)
_SOFTWARE_HINT = re.compile(
    r"software|embedded\s+software|firmware|\bdata\b|devops|cloud|\bit\b|digital|web|app\b|qa\b|test\s+automation"
    r"|\basic\b|\bfpga\b|\brtl\b|\bvlsi\b|verification|autosar|silicon",
    re.IGNORECASE,
)


def is_data_role(title: str | None) -> bool:
    if not title:
        return False
    if _WAREHOUSE_NOISE.search(title) and not _DATA_WORD.search(title):
        return False
    return bool(_DATA_INCLUDE.search(title)) and not _DATA_EXCLUDE.search(title)


def is_tech_role(title: str | None) -> bool:
    """Data roles + software, QA/testing, UI/UX design, DevOps/cloud, security, IT."""
    if not title:
        return False
    if _WAREHOUSE_NOISE.search(title) and not _DATA_WORD.search(title):
        return False
    if _NON_TECH.search(title) and not _SOFTWARE_HINT.search(title):
        return False
    if _DATA_EXCLUDE.search(title):
        return False
    if _AI_WORD.search(title) and _AI_NON_TECH.search(title) and not _AI_ROLE_WORD.search(title):
        return False
    return bool(_DATA_INCLUDE.search(title) or _TECH_INCLUDE.search(title))


# ------------------------------------------------- business roles at tech companies
# Account managers, customer success and project managers. Only kept from company career
# sites (our board registry is tech, fintech and digital companies); dbt then keeps them only
# for companies in tech / fintech industries (fct_job_postings). Track "Clients & Projects".
_BUSINESS_ROLE = re.compile(
    r"""
    customer\s+success | client\s+success
    | \b(key\s+)?account\s+(manager|director|lead) | \bkey\s+account | client\s+(account\s+)?manager | relationship\s+manager
    | \b(project|program|programme)\s+(manager|lead|coordinator|director) | \bproject\s+management\s+(officer|specialist|lead)
    | \bprojektleit | chef\s+de\s+projet | jefe\s+de\s+proyecto
    """,
    re.IGNORECASE | re.VERBOSE,
)
_BUSINESS_NOT = re.compile(
    r"construction|civil|mechanical|electrical|\bmep\b|clinical|medical|\bevents?\b|site\s+(manager|project)|interior|fit[\s-]?out"
    r"|architectur|real\s+estate|facilit|marketing|creative|\bhr\b|human\s+resources|recruit|talent|legal|warehouse|logistics",
    re.IGNORECASE,
)


def is_business_role(title: str | None) -> bool:
    """Account manager, customer success or project manager (not construction / events / marketing projects)."""
    return bool(title) and bool(_BUSINESS_ROLE.search(title)) and not _BUSINESS_NOT.search(title)


def is_board_role(title: str | None) -> bool:
    """What we keep from a company's own career site: tech roles plus the business roles above."""
    return is_tech_role(title) or is_business_role(title)
