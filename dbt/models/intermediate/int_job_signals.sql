-- Signals that matter for people applying from abroad (e.g. from Egypt to the Gulf or Europe),
-- read from the job title and description text:
--   nationals_only            "Saudi nationals only", "UAE National", Emiratisation / Saudization roles
--   arabic_required           Arabic named as a required or spoken language
--   offers_visa_or_relocation visa sponsorship / relocation support offered (and not explicitly refused)
with d as (
    select job_id, job_title, lower(coalesce(job_title, '') || ' ' || coalesce(description_text, '')) as txt
    from {{ ref('int_postings_deduped') }}
)

select
    job_id,
    (
        job_title ~* '\m(emirati|uae\s+nationals?|saudi\s+nationals?|qatari\s+nationals?|kuwaiti\s+nationals?|omani\s+nationals?|bahraini\s+nationals?)\M|\m(saudis?|emiratis?|qataris?|kuwaitis?|omanis?|bahrainis?)\s+only\M'
        or txt ~ '(saudi|emirati|uae|qatari|kuwaiti|omani|bahraini)\s+nationals?\s+(only|are\s+required|is\s+required|required)|only\s+(open\s+to\s+)?(saudi|emirati|uae|qatari|kuwaiti|omani|bahraini)\s+(nationals?|citizens)|nationals?\s+only|(saudization|saudisation|emiratization|emiratisation|qatarization|qatarisation|omanization|omanisation)|must\s+be\s+(a\s+)?(saudi|emirati|uae|qatari|kuwaiti|omani|bahraini)\s+(national|citizen)'
    )                                                                       as nationals_only,
    (
        job_title ~* '\marabic\M'
        or txt ~ '(fluent|fluency|proficien\w*|native|bilingual|speak\w*|written\s+and\s+(spoken|verbal)|verbal\s+and\s+written|excellent|strong|good\s+command\s+of)\W+(\w+\W+){0,4}arabic|arabic\W+(\w+\W+){0,3}(speaker|speaking|language|required|is\s+a\s+must|essential|is\s+mandatory|fluency|proficiency|skills)|arabic\s+(and|&|/)\s+english|english\s+(and|&|/)\s+arabic'
    )                                                                       as arabic_required,
    (
        txt ~ 'visa\s+sponsor|sponsor(ship)?\s+(of\s+)?(your\s+|a\s+)?(work\s+)?(visa|permit)|relocation\s+(support|package|assistance|bonus|allowance|budget|help|is\s+(provided|offered|available|supported))|(help|support|assist)\s+(you\s+)?(with\s+)?(your\s+)?relocat|visa\s+(support|assistance|and\s+relocation)|work\s+permit\s+(support|assistance)|blue\s+card|we\s+(offer|provide)\s+relocation'
        and txt !~ '(no|not|unable\s+to|cannot|can''t|do\s+not|don''t|won''t|will\s+not|without)\s+(\w+\s+){0,3}(visa\s+)?sponsor|sponsorship\s+(is\s+)?not\s+(available|provided|offered|possible)|no\s+relocation|relocation\s+(is\s+)?not\s+(available|provided|offered)'
    )                                                                       as offers_visa_or_relocation
from d
