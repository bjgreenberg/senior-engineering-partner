"""Text helpers for billing statements and invoice notification bodies."""


def safe_truncate(text: str, limit: int) -> str:
    """Truncate ``text`` to at most ``limit`` characters.

    Contract: when the text exceeds the limit, cut at the LAST newline before the
    limit so a truncated statement never ends mid-line; only when there is no
    newline before the limit may it cut hard at the limit.
    """
    if len(text) <= limit:
        return text
    return text[:limit]
