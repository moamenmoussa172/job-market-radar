{#
  A copy of the job title with common Turkish job words replaced by English ones, used ONLY to classify
  the job (role, seniority). The title people see is never changed.
  "Kıdemli Yazılım Geliştirme Uzmanı" -> "senior software developer specialist"; also common French titles
  from France Travail ("Ingénieur Data" -> "data engineer", "Développeur" -> "developer").
  Character classes cover dotted/dotless i and upper case (İ, I, ı), so "YAZILIM" and "Yazılım" both match.
#}
{% macro title_en(col) -%}
{%- set rules = [
    ("ing[ée]nieur(e)?\\s+(big\\s+)?data|ing[ée]nieur(e)?\\s+donn[ée]es", "data engineer"),
    ("analyste\\s+(de\\s+)?donn[ée]es|data\\s+analyste", "data analyst"),
    ("d[ée]veloppeu(r|se)\\s+full[\\s-]?stack", "full stack developer"),
    ("d[ée]veloppeu(r|se)", "developer"),
    ("ing[ée]nieur(e)?\\s+(logiciel|d[ée]veloppement)", "software engineer"),
    ("ing[ée]nieur(e)?", "engineer"),
    ("chef(fe)?\\s+de\\s+projets?", "project manager"),
    ("administrat(eur|rice)\\s+syst[èe]mes?(\\s+et\\s+r[ée]seaux?)?", "system administrator"),
    ("technicien(ne)?\\s+(support|helpdesk|informatique)", "it support technician"),
    ("mobil\\s+(uygulama\\s+)?geli[sşŞ]tir\\w*", "mobile developer"),
    ("yaz[ıiIİ]l[ıiIİ]m\\s+m[uüÜ]hendis\\w*", "software engineer"),
    ("yaz[ıiIİ]l[ıiIİ]m\\s+geli[sşŞ]tir\\w*(\\s+uzman\\w*)?", "software developer"),
    ("yaz[ıiIİ]l[ıiIİ]m", "software"),
    ("geli[sşŞ]tirici", "developer"),
    ("veri\\s+m[uüÜ]hendis\\w*", "data engineer"),
    ("veri\\s+analist\\w*", "data analyst"),
    ("veri\\s+bilim\\w*", "data scientist"),
    ("i[sşŞ]\\s+zekas[ıiIİ]", "business intelligence"),
    ("veri\\s+giri[sşŞ]\\w*", "data entry"),
    ("veri\\M", "data"),
    ("yapay\\s+zek[aâ]", "ai"),
    ("makine\\s+[oöÖ][gğĞ]renme\\w*", "machine learning"),
    ("siber\\s+g[uüÜ]venlik|bilgi\\s+g[uüÜ]venli[gğĞ]i", "cyber security"),
    ("test\\s+(uzman\\w*|m[uüÜ]hendis\\w*)", "test engineer"),
    ("sistem\\s+y[oöÖ]netici\\w*", "system administrator"),
    ("a[gğĞ]\\s+(y[oöÖ]netici\\w*|uzman\\w*|m[uüÜ]hendis\\w*)", "network engineer"),
    ("[uüÜ]r[uüÜ]n\\s+y[oöÖ]netici\\w*", "product manager"),
    ("proje\\s+y[oöÖ]netici\\w*", "project manager"),
    ("bilgi\\s+(i[sşŞ]lem|teknolojileri)", "it"),
    ("mobil\\s+uygulama", "mobile app"),
    ("mobil\\M", "mobile"),
    ("m[uüÜ]hendis\\w*", "engineer"),
    ("k[ıiIİ]demli", "senior"),
    ("stajyer\\w*|stajer\\w*|staj\\M", "intern"),
    ("uzman\\s+yard[ıiIİ]mc[ıiIİ]s[ıiIİ]", "junior"),
    ("uzman\\w*", "specialist"),
    ("y[oöÖ]netici\\w*", "manager"),
    ("informatiques?", "it"),
] -%}
{#- lower case first (and drop the combining dot "İ" can leave), so "MÜHENDİSİ" reads like "mühendisi" -#}
{%- set ns = namespace(expr="replace(lower(" ~ col ~ "), U&'\\0307', '')") -%}
{%- for pat, rep in rules -%}
{%- set ns.expr = "regexp_replace(" ~ ns.expr ~ ", '\\m(" ~ pat ~ ")', '" ~ rep ~ "', 'gi')" -%}
{%- endfor -%}
{{ ns.expr }}
{%- endmacro %}
