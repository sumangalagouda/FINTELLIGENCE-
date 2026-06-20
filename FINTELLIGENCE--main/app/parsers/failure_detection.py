"""
failure_detection.py
=====================
Production-grade transaction status classifier for Indian bank statements.

Detects whether a transaction is SUCCESS, FAILED, REVERSED, RETURNED,
REFUNDED, BOUNCED, PENDING, or UNKNOWN using multiple layers of evidence:
keyword matching, debit-credit pair matching, reference number matching,
narration similarity, balance restoration analysis, and bank-specific
patterns — combined into a weighted confidence score.

Usage:
    from failure_detection import classify_transactions

    results = classify_transactions(transactions)
    # each transaction dict is returned with status/confidence/etc. added
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Prefer rapidfuzz (faster, C-accelerated); fall back to difflib if unavailable.
try:
    from rapidfuzz import fuzz as _rapidfuzz_fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover
    import difflib
    _HAS_RAPIDFUZZ = False
    logger.info("rapidfuzz not installed; falling back to difflib for narration similarity.")


# =============================================================================
# 1. STATUS CONSTANTS
# =============================================================================

class Status:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    RETURNED = "RETURNED"
    REFUNDED = "REFUNDED"
    BOUNCED = "BOUNCED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


# =============================================================================
# 2. KEYWORD DICTIONARIES (configurable)
# =============================================================================
# Each value is a list of regex fragments. They are compiled with
# case-insensitive word-boundary matching. Multi-word phrases use \s+ so
# that statements with inconsistent spacing ("NOT  PROCESSED") still match.

FAILED_KEYWORDS: List[str] = [
    r"FAILED", r"FAILURE", r"DECLINED", r"NOT\s+PROCESSED", r"TIMEOUT",
    r"TECHNICAL\s+ERROR", r"SYSTEM\s+ERROR", r"TXN\s+FAILED",
    r"TRANSACTION\s+FAILED", r"PAYMENT\s+FAILED", r"AUTH\s+DECLINED",
    r"INSUFFICIENT\s+FUNDS", r"INSUFFICIENT\s+BALANCE", r"INVALID\s+ACCOUNT",
    r"WRONG\s+ACCOUNT", r"ACCOUNT\s+CLOSED", r"A/?C\s+CLOSED",
    r"BENEFICIARY\s+REJECTED", r"DEBIT\s+FAILED", r"CREDIT\s+FAILED",
    r"ATM\s+DISPENSE\s+FAILURE", r"DISPENSE\s+ERROR", r"CASH\s+NOT\s+DISPENSED",
    r"MANDATE\s+REJECTED", r"NACH\s+REJECTED", r"NACH\s+FAILED",
]

REVERSED_KEYWORDS: List[str] = [
    r"REVERSAL", r"REVERSED", r"REV[\-\s]?UPI", r"UPI\s+REV(?:ERSAL)?",
    r"IMPS\s+REV(?:ERSAL)?", r"ATM\s+REVERSAL", r"AUTO\s+REVERSAL",
    r"REVERSED\s+TRANSACTION", r"TXN\s+REVERSED", r"REV\s+OF\s+UPI",
    r"REVERSAL\s+OF\s+UPI", r"UPI\s+REVERSAL\s+CREDIT",
]

RETURNED_KEYWORDS: List[str] = [
    r"RETURN(?:ED)?", r"\bRTRN\b", r"\bRTN\b", r"ACH\s+RETURN",
    r"NACH\s+RETURN", r"ECS\s+RETURN", r"NEFT\s+RETURN", r"RTGS\s+RETURN",
    r"BUNCH\s+RETURN", r"PAYMENT\s+RETURNED",
]

BOUNCED_KEYWORDS: List[str] = [
    r"BOUNCE", r"BOUNCED", r"DISHONOUR(?:ED)?", r"DISHONOR(?:ED)?",
    r"CHQ\s+RETURN", r"CHEQUE\s+RETURN", r"CHEQUE\s+BOUNCED",
    r"CHQ\s+DISHONOU?RED", r"CHQ\s+RTN",
]

REFUND_KEYWORDS: List[str] = [
    r"REFUND(?:ED)?", r"MERCHANT\s+REFUND", r"ORDER\s+REFUND",
    r"REFUND\s+CREDIT", r"AMOUNT\s+REFUNDED", r"PARTIAL\s+REFUND",
]

PENDING_KEYWORDS: List[str] = [
    r"PENDING", r"IN\s+PROCESS", r"AWAITING\s+CONFIRMATION",
    r"UNDER\s+PROCESS", r"PROCESSING", r"AWAITING\s+SETTLEMENT",
]

# -----------------------------------------------------------------------
# Protected categories: these must NEVER be classified as FAILED even if
# they superficially contain words like "reversal" (e.g. "CHARGE REVERSAL"
# is a goodwill credit, not a failed transaction).
# -----------------------------------------------------------------------

PROTECTED_KEYWORDS: List[str] = [
    r"SALARY", r"SAL\s+CREDIT", r"INTEREST\s+CREDIT(?:ED)?", r"\bINT\.?\s*CR\b",
    r"CASHBACK", r"CASH\s+BACK", r"REWARD", r"INCENTIVE", r"BONUS",
    r"CHARGE\s+REVERSAL", r"CHARGES\s+REVERSED", r"FEE\s+REVERSAL",
    r"GST\s+REVERSAL", r"GST\s+REVERSED", r"ANNUAL\s+FEE\s+REVERSAL",
    r"LATE\s+(?:FEE|PAYMENT\s+CHARGE)\s+REVERSAL", r"WAIVER",
    r"DIVIDEND", r"REFERRAL\s+BONUS",
]

# =============================================================================
# 3. BANK-SPECIFIC PATTERN DICTIONARIES
# =============================================================================
# Patterns that strongly correlate with reversal/failure narrations used by
# specific Indian banks. Matching one of these adds bank-specific confidence
# on top of the generic keyword layer.

BANK_SPECIFIC_PATTERNS: Dict[str, List[str]] = {
    "SBI": [r"REV[\-\s]?UPI", r"UPI\s+REVERSAL", r"UPI/REV/"],
    "HDFC": [r"UPI\s+REVERSAL\s+CREDIT", r"REVERSAL[\-\s]?UPI", r"IMPS\s+REVERSAL"],
    "ICICI": [r"REVERSAL\s+OF\s+UPI", r"UPI\s+RET\s+REV", r"REV:UPI"],
    "AXIS": [r"FAILED\s+UPI\s+TXN", r"UPI\s+TXN\s+FAILED", r"REV/UPI/"],
    "KOTAK": [r"UPI\s+REV\b", r"REVERSAL-UPI", r"KKBK.*REV"],
    "CANARA": [r"UPI\s+REV\b", r"CANARA.*REVERSAL"],
    "PNB": [r"PNB.*REV(?:ERSAL)?", r"UPI/RET/"],
    "BOB": [r"BOB.*REVERSAL", r"BARODA.*REV"],
    "UNION BANK": [r"UNION.*REV(?:ERSAL)?", r"UBI.*RET"],
}

# Normalize bank name aliases to the keys above
BANK_ALIASES: Dict[str, str] = {
    "STATE BANK OF INDIA": "SBI", "SBIN": "SBI", "SBI": "SBI",
    "HDFC BANK": "HDFC", "HDFC": "HDFC",
    "ICICI BANK": "ICICI", "ICICI": "ICICI",
    "AXIS BANK": "AXIS", "AXIS": "AXIS", "UTIB": "AXIS",
    "KOTAK MAHINDRA BANK": "KOTAK", "KOTAK": "KOTAK", "KKBK": "KOTAK",
    "CANARA BANK": "CANARA", "CANARA": "CANARA", "CNRB": "CANARA",
    "PUNJAB NATIONAL BANK": "PNB", "PNB": "PNB",
    "BANK OF BARODA": "BOB", "BOB": "BOB", "BARB": "BOB",
    "UNION BANK OF INDIA": "UNION BANK", "UNION BANK": "UNION BANK", "UBIN": "UNION BANK",
}


# =============================================================================
# 4. REFERENCE NUMBER EXTRACTION PATTERNS
# =============================================================================
# Indian bank narrations embed reference numbers in many formats, e.g.:
#   "UPI/123456789012/AMAZON PAY"
#   "IMPS-987654321098-JOHN DOE"
#   "NEFT/N123456789012/ACME CORP"
#   "RTGS/HDFCR12024061900001/XYZ LTD"
#   "CHQ NO 000123"
# We extract a generic reference token per transaction; if two transactions
# share the same token, that's strong evidence of a linked pair.

REFERENCE_PATTERNS: List[Tuple[str, str]] = [
    ("UPI", r"UPI[/\-\s:]+(\d{10,16})"),
    ("IMPS", r"IMPS[/\-\s:]+(\d{10,18})"),
    ("NEFT", r"NEFT[/\-\s:]+([A-Z0-9]{10,20})"),
    ("RTGS", r"RTGS[/\-\s:]+([A-Z0-9]{10,20})"),
    ("UTR", r"UTR[/\-\s:]*([A-Z0-9]{10,22})"),
    ("CHEQUE", r"CHQ\.?\s*(?:NO\.?)?[/\-\s:]*(\d{4,10})"),
    ("GENERIC_REF", r"REF(?:ERENCE)?[/\-\s:#]*([A-Z0-9]{8,22})"),
    # Bare long digit sequences (10-18 digits) as last-resort reference
    ("BARE_DIGITS", r"\b(\d{10,18})\b"),
]


def extract_reference(description: str, explicit_ref: Optional[str] = None) -> Optional[str]:
    """
    Extract a normalized reference token from a transaction's description,
    preferring an explicit reference_number field if supplied.
    Returns the bare alphanumeric token (no label), or None.
    """
    if explicit_ref and str(explicit_ref).strip():
        token = str(explicit_ref).strip().upper()
        # Strip common non-alphanumeric noise
        token = re.sub(r"[^A-Z0-9]", "", token)
        if len(token) >= 6:
            return token

    if not description:
        return None
    desc = description.upper()
    for _label, pattern in REFERENCE_PATTERNS:
        m = re.search(pattern, desc)
        if m:
            return m.group(1)
    return None


# =============================================================================
# 5. CONFIDENCE SCORING WEIGHTS
# =============================================================================

WEIGHTS = {
    "failed_keyword": 50,
    "reversed_keyword": 30,
    "returned_keyword": 30,
    "bounced_keyword": 30,
    "refund_keyword": 25,
    "pending_keyword": 20,
    "same_amount": 40,
    "same_reference": 50,
    "narration_similarity_high": 20,   # similarity > 80%
    "narration_similarity_medium": 10, # similarity 60-80%
    "balance_restored": 20,
    "time_lt_30min": 30,
    "time_30min_24h": 20,
    "time_2_7days": 10,
    "bank_specific_pattern": 20,
}

# Normalization ceiling for converting raw weighted scores into a 0-1
# confidence float. NOT the sum of every possible weight — keyword
# categories are mutually exclusive in practice (a narration rarely matches
# both FAILED and BOUNCED keywords), so summing all of them would make
# realistic, well-evidenced scores look artificially low. Instead we use
# the score of a "maximally confident realistic case": one keyword match
# (50) + bank pattern (20) + same amount (40) + same reference (50) +
# high narration similarity (20) + balance restored (20) + tight time
# window (30) = 230. Scores above this still clamp to 1.0.
_MAX_POSSIBLE_SCORE = 230.0


# =============================================================================
# 6. OUTPUT DATA STRUCTURE
# =============================================================================

@dataclass
class ClassificationResult:
    status: str = Status.UNKNOWN
    confidence: float = 0.0
    failure_reason: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)
    linked_transaction_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "failure_reason": self.failure_reason,
            "matched_rules": self.matched_rules,
            "linked_transaction_id": self.linked_transaction_id,
        }


# =============================================================================
# 7. KEYWORD MATCHING ENGINE
# =============================================================================

def _compile_keyword_group(keywords: List[str]) -> re.Pattern:
    """Compile a list of regex fragments into one case-insensitive,
    word-boundary-respecting alternation pattern."""
    parts = [rf"\b(?:{kw})\b" for kw in keywords]
    return re.compile("|".join(parts), re.IGNORECASE)


_COMPILED_KEYWORDS = {
    "FAILED": _compile_keyword_group(FAILED_KEYWORDS),
    "REVERSED": _compile_keyword_group(REVERSED_KEYWORDS),
    "RETURNED": _compile_keyword_group(RETURNED_KEYWORDS),
    "BOUNCED": _compile_keyword_group(BOUNCED_KEYWORDS),
    "REFUND": _compile_keyword_group(REFUND_KEYWORDS),
    "PENDING": _compile_keyword_group(PENDING_KEYWORDS),
}
_COMPILED_PROTECTED = _compile_keyword_group(PROTECTED_KEYWORDS)

_COMPILED_BANK_PATTERNS: Dict[str, re.Pattern] = {
    bank: _compile_keyword_group(patterns)
    for bank, patterns in BANK_SPECIFIC_PATTERNS.items()
}


def is_protected_category(description: str) -> bool:
    """True if the narration matches a protected category (salary, interest,
    cashback, rewards, charge/GST reversal, etc.) that must never be
    classified as FAILED/BOUNCED/RETURNED."""
    if not description:
        return False
    return bool(_COMPILED_PROTECTED.search(description))


def match_keywords(description: str) -> Dict[str, List[str]]:
    """
    Run all keyword groups against a description.
    Returns a dict of {category: [matched substrings]} for every category
    that matched at least once.
    """
    matches: Dict[str, List[str]] = {}
    if not description:
        return matches
    for category, pattern in _COMPILED_KEYWORDS.items():
        found = pattern.findall(description)
        if found:
            matches[category] = list(dict.fromkeys(found))  # de-dup, preserve order
    return matches


def normalize_bank_name(bank_name: Optional[str]) -> Optional[str]:
    if not bank_name:
        return None
    key = str(bank_name).strip().upper()
    return BANK_ALIASES.get(key, key if key in BANK_SPECIFIC_PATTERNS else None)


def match_bank_specific_pattern(description: str, bank_name: Optional[str]) -> bool:
    """True if description matches a known reversal/failure pattern specific
    to the given bank's narration conventions."""
    if not description:
        return False
    normalized = normalize_bank_name(bank_name)
    if not normalized or normalized not in _COMPILED_BANK_PATTERNS:
        return False
    return bool(_COMPILED_BANK_PATTERNS[normalized].search(description))


# =============================================================================
# 8. SINGLE-TRANSACTION SCORING LAYER
# =============================================================================
# Scores keyword + bank-pattern evidence for ONE transaction in isolation,
# before any pairwise (cross-transaction) evidence is added in layer 2.

def _score_single_transaction(txn: Dict[str, Any]) -> Tuple[float, List[str], Optional[str]]:
    """
    Returns (score, matched_rules, failure_reason_candidate) based purely on
    this transaction's own description and bank, ignoring other transactions.
    """
    description = str(txn.get("description") or "")
    bank_name = txn.get("bank_name")

    score = 0.0
    rules: List[str] = []
    reason: Optional[str] = None

    # Protected categories short-circuit failure/bounce/return keyword scoring,
    # but PENDING and explicit REFUND keywords are still allowed to apply,
    # since e.g. "cashback pending" or "merchant refund" can co-occur.
    protected = is_protected_category(description)

    keyword_matches = match_keywords(description)

    if "FAILED" in keyword_matches and not protected:
        score += WEIGHTS["failed_keyword"]
        rules.append("failed_keyword")
        reason = reason or f"Failure keyword matched: {keyword_matches['FAILED'][0]}"

    if "REVERSED" in keyword_matches and not protected:
        score += WEIGHTS["reversed_keyword"]
        rules.append("reversed_keyword")
        reason = reason or f"Reversal keyword matched: {keyword_matches['REVERSED'][0]}"

    if "RETURNED" in keyword_matches and not protected:
        score += WEIGHTS["returned_keyword"]
        rules.append("returned_keyword")
        reason = reason or f"Return keyword matched: {keyword_matches['RETURNED'][0]}"

    if "BOUNCED" in keyword_matches and not protected:
        score += WEIGHTS["bounced_keyword"]
        rules.append("bounced_keyword")
        reason = reason or f"Bounce keyword matched: {keyword_matches['BOUNCED'][0]}"

    if "REFUND" in keyword_matches:
        score += WEIGHTS["refund_keyword"]
        rules.append("refund_keyword")
        reason = reason or f"Refund keyword matched: {keyword_matches['REFUND'][0]}"

    if "PENDING" in keyword_matches:
        score += WEIGHTS["pending_keyword"]
        rules.append("pending_keyword")
        reason = reason or f"Pending keyword matched: {keyword_matches['PENDING'][0]}"

    if not protected and match_bank_specific_pattern(description, bank_name):
        score += WEIGHTS["bank_specific_pattern"]
        rules.append("bank_specific_pattern")
        reason = reason or f"Bank-specific reversal pattern matched ({normalize_bank_name(bank_name)})"

    return score, rules, reason


# =============================================================================
# 9. NARRATION SIMILARITY
# =============================================================================

def narration_similarity(desc_a: str, desc_b: str) -> float:
    """
    Returns a 0-100 similarity score between two narrations.
    Uses rapidfuzz.fuzz.token_sort_ratio if available (robust to word
    order, e.g. "UPI AMAZON PAY" vs "UPI REVERSAL AMAZON PAY" still scores
    highly because shared tokens dominate), else falls back to difflib's
    SequenceMatcher ratio.
    """
    if not desc_a or not desc_b:
        return 0.0
    a, b = desc_a.upper().strip(), desc_b.upper().strip()
    if _HAS_RAPIDFUZZ:
        return _rapidfuzz_fuzz.token_sort_ratio(a, b)
    return difflib.SequenceMatcher(None, a, b).ratio() * 100.0


# =============================================================================
# 10. TIME-BUCKET CLASSIFICATION FOR PAIR MATCHING
# =============================================================================

def _time_bucket_score(delta: timedelta) -> Tuple[float, str]:
    """
    Maps a time delta between two candidate-paired transactions to a
    (weight, label) tuple per the required buckets:
      0-30 min:        very strong reversal signal
      30 min - 24 hr:  possible reversal
      2-7 days:        possible refund
      > 7 days:        likely refund/reimbursement (low/no time weight)
    """
    seconds = abs(delta.total_seconds())
    minutes = seconds / 60.0
    hours = seconds / 3600.0
    days = seconds / 86400.0

    if minutes <= 30:
        return WEIGHTS["time_lt_30min"], "very_strong_reversal_signal_0_30min"
    if hours <= 24:
        return WEIGHTS["time_30min_24h"], "possible_reversal_30min_24h"
    if 2 <= days <= 7:
        return WEIGHTS["time_2_7days"], "possible_refund_2_7days"
    if days > 7:
        return 0.0, "likely_refund_reimbursement_gt_7days"
    # Between 24h and 2 days: weak/no signal, but not zero — treat as a
    # faint possible-reversal tail rather than silently dropping it.
    return 0.0, "gap_24h_to_2days_weak_signal"


# =============================================================================
# 11. DEBIT-CREDIT PAIR MATCHING LAYER
# =============================================================================
# Cross-transaction evidence: for each debit, look for a later (or nearby)
# opposite-direction credit of the same amount, optionally confirmed by a
# shared reference number, narration similarity, and balance restoration.

AMOUNT_TOLERANCE = 0.01  # paise-level float tolerance


def _amounts_match(a: float, b: float) -> bool:
    return abs((a or 0.0) - (b or 0.0)) <= AMOUNT_TOLERANCE


def _txn_amount_and_direction(txn: Dict[str, Any]) -> Tuple[float, str]:
    """Returns (amount, direction) where direction is 'debit' or 'credit'."""
    debit = txn.get("debit") or 0.0
    credit = txn.get("credit") or 0.0
    if debit and not credit:
        return debit, "debit"
    if credit and not debit:
        return credit, "credit"
    # Both zero or both populated (unusual) — treat larger as the direction
    if debit >= credit:
        return debit, "debit"
    return credit, "credit"


def find_pair_evidence(
    txn: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    txn_ref: Optional[str],
) -> Tuple[float, List[str], Optional[str], Optional[str]]:
    """
    Search `candidates` (all OTHER transactions) for the best opposite-
    direction match to `txn`. Returns:
        (pair_score, matched_rules, linked_transaction_id, narration_match_text)

    "Best" = highest combined score across amount/time/reference/narration/
    balance evidence; ties broken by smallest time delta.
    """
    amount, direction = _txn_amount_and_direction(txn)
    if amount <= 0:
        return 0.0, [], None, None
    opposite_direction = "credit" if direction == "debit" else "debit"

    txn_date = txn.get("date")
    txn_desc = str(txn.get("description") or "")

    best_score = 0.0
    best_rules: List[str] = []
    best_id: Optional[str] = None
    best_narration: Optional[str] = None
    best_time_delta: Optional[timedelta] = None

    for other in candidates:
        if other.get("transaction_id") == txn.get("transaction_id"):
            continue
        other_amount, other_direction = _txn_amount_and_direction(other)
        if other_direction != opposite_direction:
            continue
        if not _amounts_match(amount, other_amount):
            continue

        rules: List[str] = ["same_amount"]
        score = WEIGHTS["same_amount"]

        # --- Time proximity ---
        other_date = other.get("date")
        if isinstance(txn_date, datetime) and isinstance(other_date, datetime):
            delta = other_date - txn_date
            # Only consider the credit happening at/after the debit (or vice
            # versa) as a plausible reversal/refund direction; same-instant
            # is allowed (delta == 0).
            time_weight, time_label = _time_bucket_score(delta)
            if time_weight > 0:
                score += time_weight
                rules.append(f"time_bucket:{time_label}")
        else:
            delta = None

        # --- Reference number match ---
        other_ref = extract_reference(
            str(other.get("description") or ""), other.get("reference_number")
        )
        if txn_ref and other_ref and txn_ref == other_ref:
            score += WEIGHTS["same_reference"]
            rules.append("same_reference")

        # --- Narration similarity ---
        other_desc = str(other.get("description") or "")
        similarity = narration_similarity(txn_desc, other_desc)
        if similarity > 80:
            score += WEIGHTS["narration_similarity_high"]
            rules.append(f"narration_similarity_high:{similarity:.0f}")
        elif similarity >= 60:
            score += WEIGHTS["narration_similarity_medium"]
            rules.append(f"narration_similarity_medium:{similarity:.0f}")

        # --- Balance restoration ---
        if _check_balance_restored(txn, other, direction):
            score += WEIGHTS["balance_restored"]
            rules.append("balance_restored")

        if score > best_score or (
            score == best_score
            and delta is not None
            and (best_time_delta is None or abs(delta) < abs(best_time_delta))
        ):
            best_score = score
            best_rules = rules
            best_id = other.get("transaction_id")
            best_narration = other_desc
            best_time_delta = delta

    return best_score, best_rules, best_id, best_narration


def _check_balance_restored(
    txn: Dict[str, Any], other: Dict[str, Any], direction: str
) -> bool:
    """
    Detects the pattern: balance drops by debit amount, then a later credit
    of the same amount restores balance to (approximately) its pre-debit
    level. Requires both transactions to carry a running `balance`.
    Handles missing balances gracefully (returns False, never raises).
    """
    debit_txn = txn if direction == "debit" else other
    credit_txn = other if direction == "debit" else txn

    debit_balance = debit_txn.get("balance")
    credit_balance = credit_txn.get("balance")
    debit_amount = debit_txn.get("debit")
    credit_amount = credit_txn.get("credit")

    if debit_balance is None or credit_balance is None:
        return False
    if debit_amount is None or credit_amount is None:
        return False

    # Balance immediately before the debit, inferred from balance-after-debit
    # + debit amount. We don't have a guaranteed "balance before" field, so
    # we approximate: post-credit balance should be close to
    # (post-debit balance + credit amount), which is trivially true unless
    # other transactions intervened. The stronger signal is that the credit
    # amount equals the debit amount AND the credit balance equals the
    # debit's pre-transaction balance (debit_balance + debit_amount).
    implied_pre_debit_balance = debit_balance + debit_amount
    return _amounts_match(credit_balance, implied_pre_debit_balance)


# =============================================================================
# 12. CLASSIFICATION RULES
# =============================================================================

def _classify_from_score(
    total_score: float,
    keyword_matches: Dict[str, List[str]],
    protected: bool,
    has_pair_link: bool,
) -> str:
    """
    Maps accumulated evidence to a final status label.
    Order matters — checked top to bottom, first match wins.
    """
    confidence = min(total_score / _MAX_POSSIBLE_SCORE, 1.0)

    has_failed_kw = "FAILED" in keyword_matches and not protected
    has_reversed_kw = "REVERSED" in keyword_matches and not protected
    has_returned_kw = "RETURNED" in keyword_matches and not protected
    has_bounced_kw = "BOUNCED" in keyword_matches and not protected
    has_refund_kw = "REFUND" in keyword_matches
    has_pending_kw = "PENDING" in keyword_matches

    # Strong cross-evidence (pair matched + high score) => REVERSED,
    # even without an explicit "reversal" keyword (e.g. plain UPI debit
    # immediately undone by a matching credit with same reference).
    if confidence >= 0.90:
        return Status.REVERSED

    if confidence >= 0.80 and has_failed_kw:
        return Status.FAILED

    if has_refund_kw and has_pair_link:
        return Status.REFUNDED

    if has_bounced_kw:
        return Status.BOUNCED

    if has_returned_kw:
        return Status.RETURNED

    if has_reversed_kw or (has_pair_link and confidence >= 0.60):
        return Status.REVERSED

    if has_failed_kw:
        return Status.FAILED

    if has_refund_kw:
        return Status.REFUNDED

    if has_pending_kw:
        return Status.PENDING

    return Status.SUCCESS


# =============================================================================
# 13. MAIN ORCHESTRATION
# =============================================================================

def classify_transaction(
    txn: Dict[str, Any], all_transactions: List[Dict[str, Any]]
) -> ClassificationResult:
    """
    Classify a single transaction using all evidence layers, comparing
    against `all_transactions` (the full statement) for pairwise matching.
    Never raises — degrades to UNKNOWN/SUCCESS with low confidence on
    missing/malformed data.
    """
    try:
        description = str(txn.get("description") or "")
        protected = is_protected_category(description)

        # --- Layer 1: keyword + bank-specific single-transaction scoring ---
        single_score, single_rules, reason = _score_single_transaction(txn)

        # --- Layer 2: pairwise matching (amount/time/reference/narration/balance) ---
        txn_ref = extract_reference(description, txn.get("reference_number"))
        pair_score, pair_rules, linked_id, linked_narration = find_pair_evidence(
            txn, all_transactions, txn_ref
        )

        all_rules = single_rules + pair_rules
        total_score = single_score + pair_score

        keyword_matches = match_keywords(description)
        has_pair_link = linked_id is not None and pair_score > 0

        status = _classify_from_score(
            total_score, keyword_matches, protected, has_pair_link
        )

        confidence = min(total_score / _MAX_POSSIBLE_SCORE, 1.0)

        # Edge case: nothing matched at all and the transaction is a plain
        # debit/credit with no surrounding evidence -> SUCCESS with baseline
        # confidence rather than 0, since "no evidence of failure" is itself
        # a (weaker) signal of success, not "unknown".
        if status == Status.SUCCESS and total_score == 0:
            confidence = 0.95

        # If we truly have nothing to go on (empty description, no amounts,
        # no pair) keep it conservative.
        if not description and txn.get("debit") in (None, 0) and txn.get("credit") in (None, 0):
            status = Status.UNKNOWN
            confidence = 0.0

        # Build failure_reason: only populated for non-SUCCESS, non-UNKNOWN
        failure_reason = None
        if status not in (Status.SUCCESS, Status.UNKNOWN):
            if reason:
                failure_reason = reason
            elif has_pair_link:
                failure_reason = f"Matched opposite transaction {linked_id} (amount/time/reference evidence)"
            else:
                failure_reason = f"Classified as {status} based on narration evidence"

        return ClassificationResult(
            status=status,
            confidence=confidence,
            failure_reason=failure_reason,
            matched_rules=all_rules,
            linked_transaction_id=linked_id if has_pair_link else None,
        )

    except Exception:
        logger.exception(
            "classify_transaction failed for txn_id=%s; defaulting to UNKNOWN",
            txn.get("transaction_id"),
        )
        return ClassificationResult(status=Status.UNKNOWN, confidence=0.0)


def classify_transactions(
    transactions: List[Dict[str, Any]],
    dedupe: bool = True,
) -> List[Dict[str, Any]]:
    """
    Main entry point. Classifies an entire list of normalized transactions.

    Args:
        transactions: list of transaction dicts (see module docstring for
            expected input schema).
        dedupe: if True, exact duplicate transactions (same date, amount,
            direction, and description) are detected and flagged via the
            'duplicate_transaction' rule but are NOT removed — removal is
            left to the caller, since dropping rows silently can corrupt
            running-balance reconciliation.

    Returns:
        The same list, with each transaction dict updated in place AND
        returned, adding: status, confidence, failure_reason,
        matched_rules, linked_transaction_id.
    """
    if not transactions:
        return []

    results: List[Dict[str, Any]] = []

    # Pre-compute duplicate signatures for the edge case: duplicate rows
    # (e.g. statement re-export glitches) shouldn't each independently
    # claim to be "the" reversal pair of every other duplicate.
    seen_signatures: Dict[Tuple, List[str]] = {}
    for t in transactions:
        sig = (
            t.get("date").isoformat() if isinstance(t.get("date"), datetime) else t.get("date"),
            round(t.get("debit") or 0.0, 2),
            round(t.get("credit") or 0.0, 2),
            (str(t.get("description") or "")).strip().upper(),
        )
        seen_signatures.setdefault(sig, []).append(t.get("transaction_id"))

    for txn in transactions:
        result = classify_transaction(txn, transactions)
        rules = result.matched_rules

        if dedupe:
            sig = (
                txn.get("date").isoformat() if isinstance(txn.get("date"), datetime) else txn.get("date"),
                round(txn.get("debit") or 0.0, 2),
                round(txn.get("credit") or 0.0, 2),
                (str(txn.get("description") or "")).strip().upper(),
            )
            if len(seen_signatures.get(sig, [])) > 1:
                rules = rules + ["duplicate_transaction"]

        enriched = dict(txn)
        enriched.update(result.to_dict())
        enriched["matched_rules"] = rules
        results.append(enriched)

    _propagate_pair_status(results)

    return results


def _propagate_pair_status(results: List[Dict[str, Any]]) -> None:
    """
    Post-processing pass: when a debit transaction is confidently linked to
    a credit that was classified REVERSED or REFUNDED (the credit leg
    usually carries the explicit "REVERSAL"/"REFUND" keyword), the
    originating debit should inherit that same status — from a banking
    audit perspective, the debit IS the transaction that failed/was
    reversed; it shouldn't show as plain SUCCESS just because the keyword
    happened to land on the credit narration instead.

    Only applies when the debit's own classification didn't already assign
    a more specific status (e.g. an explicit FAILED keyword on the debit
    itself is left untouched, since "failed then refunded" is meaningfully
    different from "reversed").
    Mutates `results` in place.
    """
    by_id = {r.get("transaction_id"): r for r in results}

    for r in results:
        if r.get("status") not in (Status.REVERSED, Status.REFUNDED, Status.BOUNCED, Status.RETURNED):
            continue
        linked_id = r.get("linked_transaction_id")
        if not linked_id or linked_id not in by_id:
            continue

        counterpart = by_id[linked_id]
        # Only overwrite the counterpart if it's currently a neutral SUCCESS
        # with no competing keyword-based status of its own.
        if counterpart.get("status") != Status.SUCCESS:
            continue
        # Avoid overwriting a transaction that itself matched explicit
        # failure-category keywords under a different rule path.
        if any(rule in counterpart.get("matched_rules", [])
               for rule in ("failed_keyword", "bounced_keyword", "returned_keyword", "pending_keyword")):
            continue

        counterpart["status"] = r["status"]
        counterpart["confidence"] = max(counterpart.get("confidence", 0.0), r["confidence"])
        counterpart["linked_transaction_id"] = r.get("transaction_id")
        if not counterpart.get("failure_reason"):
            counterpart["failure_reason"] = (
                f"Linked to {r['transaction_id']} which was classified {r['status']} "
                f"(paired debit/credit evidence)"
            )
        if "paired_with_classified_counterpart" not in counterpart.get("matched_rules", []):
            counterpart["matched_rules"] = counterpart.get("matched_rules", []) + [
                "paired_with_classified_counterpart"
            ]
