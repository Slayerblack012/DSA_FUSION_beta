"""
DSA AutoGrader - PEP8 Style Checker.

Checks code for PEP8 violations and applies spaghetti-code penalties.
"""

from typing import List, Tuple

from app.services.grading.constants import SCORING_CONSTANTS, CodeFeatures

# ═══════════════════════════════════════════
#  PEP8 Score
# ═══════════════════════════════════════════


def check_pep8(code: str) -> Tuple[int, List[str]]:
    """
    Check PEP8 style violations.

    Returns:
        (score, list_of_notes)
    """
    notes: List[str] = []
    score = SCORING_CONSTANTS.MAX_PEP8_SCORE

    # Tabs
    if "\t" in code:
        score -= SCORING_CONSTANTS.PEP8_TAB_PENALTY
        notes.append("PEP8: Sử dụng phím Tab thay vì Space (-2đ)")

    # Long lines
    lines = code.split("\n")
    long_lines = _get_long_line_numbers(lines, SCORING_CONSTANTS.PEP8_LINE_LENGTH)

    if long_lines:
        deduction = _calculate_line_length_deduction(len(long_lines))
        score -= deduction
        notes.append(_format_line_length_note(long_lines, deduction))

    return score, notes


def _get_long_line_numbers(lines: List[str], max_length: int) -> List[str]:
    """Get line numbers (1-indexed) that exceed *max_length*."""
    return [str(i + 1) for i, line in enumerate(lines) if len(line) > max_length]


def _calculate_line_length_deduction(long_line_count: int) -> int:
    """Calculate PEP8 deduction based on number of long lines."""
    return min(
        SCORING_CONSTANTS.PEP8_MAX_LINE_DEDUCTION,
        long_line_count // SCORING_CONSTANTS.PEP8_LINES_PER_DEDUCTION + 1,
    )


def _format_line_length_note(long_lines: List[str], deduction: int) -> str:
    """Format PEP8 line-length violation note."""
    displayed = long_lines[:3]
    suffix = "..." if len(long_lines) > 3 else ""
    lines_str = ", ".join(displayed) + suffix
    max_len = SCORING_CONSTANTS.PEP8_LINE_LENGTH
    return f"PEP8: Dòng {lines_str} quá dài (>{max_len} ký tự) (-{deduction}đ)"


# ═══════════════════════════════════════════
#  Spaghetti-Code Detector
# ═══════════════════════════════════════════


def apply_spaghetti_penalties(
    pep8_score: int,
    features: CodeFeatures,
) -> Tuple[int, List[str]]:
    """Apply penalties for spaghetti code and return (adjusted_score, notes)."""
    notes: List[str] = []

    if features.global_var_count > SCORING_CONSTANTS.GLOBAL_VARS_THRESHOLD:
        pep8_score = max(0, pep8_score - SCORING_CONSTANTS.PEP8_SPAGHETTI_PENALTY)
        notes.append(
            f"Code rối: Sử dụng {features.global_var_count} biến toàn cục (-2đ)"
        )

    if features.long_func_count > 0:
        pep8_score = max(0, pep8_score - SCORING_CONSTANTS.PEP8_SPAGHETTI_PENALTY)
        notes.append(
            f"Code rối: Có {features.long_func_count} hàm quá dài "
            f"(>{SCORING_CONSTANTS.FUNCTION_MAX_LINES} dòng) (-2đ)"
        )

    return pep8_score, notes
