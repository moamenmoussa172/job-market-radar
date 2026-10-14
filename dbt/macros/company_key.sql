{#- Company name -> matching key: lower case, legal suffixes and country words removed,
    only letters and digits ("Paymob Egypt LLC" -> "paymob"). -#}
{% macro company_key(col) -%}
regexp_replace(
    regexp_replace(lower(coalesce({{ col }}, '')),
        '\m(inc|ltd|llc|l\.l\.c|gmbh|group|holdings?|co|company|plc|s\.?a|b\.?v|ag|se|fze|fzco|fz-llc|egypt|misr|uae|ksa|qatar|saudi\s+arabia)\M',
        '', 'g'),
    '[^a-z0-9]', '', 'g')
{%- endmacro %}
