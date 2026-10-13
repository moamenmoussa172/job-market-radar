{#- Small, defensive parsing helpers. Source APIs change formats without
    notice, so a value we can't parse becomes NULL instead of failing the run. -#}

{# HTML (possibly entity-escaped, as Greenhouse sends it) -> plain text #}
{% macro html_to_text(col) -%}
trim(regexp_replace(
    replace(replace(
        regexp_replace(
            replace(replace(replace(replace(replace(replace(coalesce({{ col }}, ''),
                '&amp;', '&'), '&lt;', '<'), '&gt;', '>'), '&quot;', '"'), '&#39;', ''''), '&nbsp;', ' '),
            '<[^>]*>', ' ', 'g'),
    '&amp;', '&'), '&nbsp;', ' '),
    '\s+', ' ', 'g'))
{%- endmacro %}

{# Text that may be an ISO timestamp, a 10-digit epoch (s) or 13-digit epoch (ms) #}
{% macro safe_timestamp(expr) -%}
case
    when ({{ expr }}) ~ '^\d{10}$' then to_timestamp(({{ expr }})::bigint)
    when ({{ expr }}) ~ '^\d{13}$' then to_timestamp(({{ expr }})::bigint / 1000.0)
    when ({{ expr }}) ~ '^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}(:?\d{2})?)?$'
        then ({{ expr }})::timestamptz
end
{%- endmacro %}

{# Text that may be a number (optionally with thousands separators) #}
{% macro safe_numeric(expr) -%}
case
    when replace(({{ expr }}), ',', '') ~ '^\d+(\.\d+)?$' then replace(({{ expr }}), ',', '')::numeric
end
{%- endmacro %}

{# jsonb value that may be a string, an array of strings, or an array of objects -> "a, b, c" #}
{% macro json_list_to_text(expr) -%}
case jsonb_typeof({{ expr }})
    when 'array' then (
        select string_agg(coalesce(e ->> 'name', e #>> '{}'), ', ')
        from jsonb_array_elements({{ expr }}) as e
    )
    when 'null' then null
    else {{ expr }} #>> '{}'
end
{%- endmacro %}
