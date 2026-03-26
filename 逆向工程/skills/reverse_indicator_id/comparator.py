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
    "YTM": "YIELD",
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
        return "low", chosen, "One round returned empty result"

    # Exact match
    if id1 == id2:
        return "high", r1.recommended_indicator_id, ""

    # Canonicalized match (abbreviation equivalence, e.g. MANU == MANUFACTURING)
    canon1 = _canon_id(r1.recommended_indicator_id)
    canon2 = _canon_id(r2.recommended_indicator_id)
    if canon1 == canon2:
        # Semantically identical — treat as high, pick shorter form
        final = _pick_better(r1, r2)
        return "high", final, f"Abbrev-equiv: R1={r1.recommended_indicator_id}, R2={r2.recommended_indicator_id}"

    # Check if one is the other plus optional modifier tokens (e.g. CGB_3Y vs CGB_YTM_3Y)
    # These are semantically equivalent — the extra token is implicit in context
    ctokens1 = set(canon1.split("_"))
    ctokens2 = set(canon2.split("_"))
    diff = ctokens1.symmetric_difference(ctokens2)
    if len(diff) <= 1 and len(ctokens1 & ctokens2) >= 2:
        # Only 1 token different and they share core meaning
        optional_modifiers = {"YIELD", "INDEX", "RATE", "PRICE", "FUTURES", "CLOSE", "SETTLE"}
        if diff.issubset(optional_modifiers):
            final = _pick_better(r1, r2)
            return "high", final, (
                f"Near-equiv (optional modifier): "
                f"R1={r1.recommended_indicator_id}, R2={r2.recommended_indicator_id}"
            )

    # Check semantic similarity: split into tokens and compare overlap
    tokens1 = set(id1.split("_"))
    tokens2 = set(id2.split("_"))

    if not tokens1 or not tokens2:
        return "low", r1.recommended_indicator_id, f"Round2 gave: {r2.recommended_indicator_id}"

    overlap = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard = len(overlap) / len(union)

    # Also check if one is substring of the other
    is_substring = id1 in id2 or id2 in id1

    if jaccard >= 0.6 or is_substring:
        # Medium consistency - pick the better one
        final = _pick_better(r1, r2)
        return (
            "medium",
            final,
            f"R1={r1.recommended_indicator_id}, R2={r2.recommended_indicator_id}",
        )

    # Check if round2 result appears in round1 alternatives or vice versa
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

    # Low consistency
    return (
        "low",
        r1.recommended_indicator_id,
        f"Divergent. R1={r1.recommended_indicator_id}, R2={r2.recommended_indicator_id}. "
        "Needs manual review.",
    )


def _pick_better(r1: RoundResult, r2: RoundResult) -> str:
    """Pick the better indicator_id between two rounds."""
    id1 = r1.recommended_indicator_id
    id2 = r2.recommended_indicator_id

    # Prefer shorter, cleaner names (less over-specified)
    # But not too short (must be meaningful)
    len1, len2 = len(id1), len(id2)

    # Prefer the one with higher confidence
    conf_rank = {"high": 3, "medium": 2, "low": 1, "": 0}
    c1 = conf_rank.get(r1.confidence.lower(), 0)
    c2 = conf_rank.get(r2.confidence.lower(), 0)

    if c1 > c2:
        return id1
    if c2 > c1:
        return id2

    # Same confidence: prefer round1 (primary) unless round2 is notably cleaner
    if len2 < len1 * 0.7:
        return id2  # Round2 is significantly more concise
    return id1


def compute_final_confidence(
    r1: RoundResult, r2: RoundResult, consistency: str
) -> str:
    """Derive overall confidence from rounds and consistency."""
    conf_rank = {"high": 3, "medium": 2, "low": 1, "": 0}

    c1 = conf_rank.get(r1.confidence.lower(), 0)
    c2 = conf_rank.get(r2.confidence.lower(), 0)
    cons = conf_rank.get(consistency, 0)

    avg = (c1 + c2 + cons) / 3

    if avg >= 2.5:
        return "high"
    if avg >= 1.5:
        return "medium"
    return "low"
