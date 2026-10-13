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
    r"software|embedded\s+software|firmware|\bdata\b|devops|cloud|\bit\b|digital|web|app\b|qa\b|test\s+automation",
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
