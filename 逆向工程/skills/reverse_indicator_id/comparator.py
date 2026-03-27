"""Compare Round 1 and Round 2 results for consistency."""

from schemas import RoundResult

# Common financial abbreviation equivalences.
# Each group maps to a canonical form for comparison purposes.
ABBREV_EQUIV = {
    "MANU": "MANUFACTURING",
    "INFRA": "INFRASTRUCTURE",
    "INVEST": "INVESTMENT",
    "GOV": "GOVERNMENT",
    "CUM": "CUMULATIVE",
}

# Core semantic tokens are more important than generic modifiers when comparing IDs.
GENERIC_MODIFIERS = {
    "YOY",
    "MOM",
    "CUM",
    "CUMULATIVE",
    "MONTHLY",
    "ANNUAL",
    "TARGET",
    "PROGRESS",
    "VALUE",
    "AMOUNT",
    "INDEX",
    "LEVEL",
    "RETURN",
}


def _canonicalize_token(token: str) -> str:
    """Map known abbreviation to canonical form."""
    return ABBREV_EQUIV.get(token, token)


def normalize(s: str) -> str:
    """Normalize indicator ID for comparison."""
    return s.strip().upper().replace("-", "_").replace(" ", "_")


def _canon_id(s: str) -> str:
    """Normalize + canonicalize all tokens for equivalence comparison."""
    tokens = normalize(s).split("_")
    return "_".join(_canonicalize_token(t) for t in tokens)


def _tokenize(s: str) -> list[str]:
    """Normalize and split an indicator ID into non-empty tokens."""
    return [t for t in normalize(s).split("_") if t]


def _core_tokens(tokens: list[str]) -> set[str]:
    """Return semantically important tokens, excluding generic modifiers."""
    return {t for t in tokens if t not in GENERIC_MODIFIERS}


def _has_same_core_meaning(tokens1: list[str], tokens2: list[str]) -> bool:
    """Check whether two IDs share the same core semantic subject."""
    core1 = _core_tokens(tokens1)
    core2 = _core_tokens(tokens2)

    if not core1 or not core2:
        return False

    if core1 == core2:
        return True

    # Allow abbreviation-equivalent forms in core tokens.
    canon_core1 = {_canonicalize_token(t) for t in core1}
    canon_core2 = {_canonicalize_token(t) for t in core2}
    return canon_core1 == canon_core2


def _score_indicator_id(indicator_id: str) -> tuple[int, int, int]:
    """Score an indicator ID for semantic completeness and naming cleanliness."""
    tokens = _tokenize(indicator_id)
    core_count = len(_core_tokens(tokens))
    token_count = len(tokens)
    length = len(indicator_id)
    return (core_count, token_count, -length)


def compare_rounds(r1: RoundResult, r2: RoundResult) -> tuple[str, str, str]:
    """
    Compare two round results.

    Returns:
        (consistency, final_indicator_id, notes)
    """
    id1 = normalize(r1.recommended_indicator_id)
    id2 = normalize(r2.recommended_indicator_id)

    if not id1 and not id2:
        return "low", "", "Both rounds returned empty indicator_id"

    if not id1 or not id2:
        chosen = id1 or id2
        return "low", chosen, "One round returned empty result; needs manual review"

    tokens1 = _tokenize(r1.recommended_indicator_id)
    tokens2 = _tokenize(r2.recommended_indicator_id)

    # Exact match
    if id1 == id2:
        return "high", _pick_better(r1, r2), ""

    # Canonicalized exact match (strict abbreviation equivalence only)
    canon1 = _canon_id(r1.recommended_indicator_id)
    canon2 = _canon_id(r2.recommended_indicator_id)
    if canon1 == canon2:
        final = _pick_better(r1, r2)
        return "high", final, (
            f"Abbrev-equiv: R1={r1.recommended_indicator_id}, "
            f"R2={r2.recommended_indicator_id}"
        )

    # Compare semantic similarity, but require the same core subject.
    token_set1 = set(tokens1)
    token_set2 = set(tokens2)

    if not token_set1 or not token_set2:
        return "low", "", "One round returned no valid tokens; needs manual review"

    overlap = token_set1 & token_set2
    union = token_set1 | token_set2
    jaccard = len(overlap) / len(union)

    if _has_same_core_meaning(tokens1, tokens2) and jaccard >= 0.6:
        final = _pick_better(r1, r2)
        return (
            "medium",
            final,
            f"R1={r1.recommended_indicator_id}, R2={r2.recommended_indicator_id}",
        )

    # Check if round2 result appears in round1 alternatives or vice versa.
    r1_alts_norm = [normalize(a) for a in r1.alternative_indicator_ids]
    r2_alts_norm = [normalize(a) for a in r2.alternative_indicator_ids]

    if id2 in r1_alts_norm or id1 in r2_alts_norm:
        final = _pick_better(r1, r2)
        return (
            "medium",
            final,
            f"Cross-match in alternatives. R1={r1.recommended_indicator_id}, "
            f"R2={r2.recommended_indicator_id}",
        )

    # Low consistency: keep a candidate for inspection, but flag manual review clearly.
    final = _pick_better(r1, r2)
    return (
        "low",
        final,
        f"Divergent. R1={r1.recommended_indicator_id}, R2={r2.recommended_indicator_id}. "
        "Needs manual review.",
    )


def _pick_better(r1: RoundResult, r2: RoundResult) -> str:
    """Pick the better indicator_id between two rounds."""
    id1 = r1.recommended_indicator_id
    id2 = r2.recommended_indicator_id

    conf_rank = {"high": 3, "medium": 2, "low": 1, "": 0}
    c1 = conf_rank.get(r1.confidence.lower(), 0)
    c2 = conf_rank.get(r2.confidence.lower(), 0)

    if c1 > c2:
        return id1
    if c2 > c1:
        return id2

    # Same confidence: prefer the semantically fuller and cleaner name.
    score1 = _score_indicator_id(id1)
    score2 = _score_indicator_id(id2)

    if score1 > score2:
        return id1
    if score2 > score1:
        return id2

    # Final fallback: prefer round1 as the primary proposal.
    return id1


def compute_final_confidence(
    r1: RoundResult, r2: RoundResult, consistency: str
) -> str:
    """Derive overall confidence from rounds and consistency."""
    conf_rank = {"high": 3, "medium": 2, "low": 1, "": 0}

    c1 = conf_rank.get(r1.confidence.lower(), 0)
    c2 = conf_rank.get(r2.confidence.lower(), 0)

    # Consistency should dominate final confidence in this workflow.
    if consistency == "low":
        if c1 >= 3 and c2 >= 3:
            return "medium"
        return "low"

    if consistency == "high":
        if c1 >= 2 and c2 >= 2:
            return "high"
        return "medium"

    # consistency == "medium"
    avg = (c1 + c2) / 2
    if avg >= 2.5:
        return "high"
    if avg >= 1.5:
        return "medium"
    return "low"
