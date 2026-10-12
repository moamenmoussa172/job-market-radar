"""Decides whether a job title belongs to the data job family we track.

The raw layer is scoped: we only land data-related postings so the
daily snapshots stay small. Fine-grained role classification
(Data Engineer vs Analyst vs BI ...) happens later in the silver layer.
"""
import re

# English terms + common German / French / Spanish / Dutch equivalents.
_INCLUDE = re.compile(
    r"""
    \bdata\b | \banalytics?\b | \banalyst\b | \bbusiness\ intelligence\b | \bbi\b
    | \betl\b | \belt\b | \bdbt\b | \bwarehous | \blakehouse\b | \bbig\ data\b
    | daten | donn[ée]es | \bdatos\b | \bdata-
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Titles that mention "data" but are not data-profession roles.
_EXCLUDE = re.compile(
    r"data\s*entry|data\s*cent(er|re)|datacenter|rechenzentrum|data\s*protection\s*officer",
    re.IGNORECASE,
)


def is_data_role(title: str | None) -> bool:
    if not title:
        return False
    return bool(_INCLUDE.search(title)) and not _EXCLUDE.search(title)
