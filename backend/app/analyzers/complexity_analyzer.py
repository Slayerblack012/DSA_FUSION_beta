"""
DSA AutoGrader - Complexity Analyzer.

Standalone module for Big-O estimation and complexity curve generation.
Extracted from scorer.py for separation of concerns.

Features:
- Big-O estimation from AST features (loop depth, recursion, algorithm detection)
- Efficient algorithm override (binary search, merge sort, etc.)
- Complexity curve data generation for visualization
- Structural complexity scoring
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("dsa.complexity")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class ASTFeatures:
    """AST analysis results relevant for complexity estimation."""
    max_loop_depth: int = 0
    has_recursion: bool = False
    has_div2: bool = False  # Division by 2 (binary search indicator)
    has_nested_loops: bool = False
    algorithms: List[str] = field(default_factory=list)
    function_count: int = 0
    class_count: int = 0


@dataclass
class ComplexityReport:
    """Result of complexity analysis."""
    estimated_big_o: str = "O(n)"
    score: float = 1.0  # Normalized 0.0 - 1.0
    max_score: float = 1.0
    loop_depth: int = 0
    has_recursion: bool = False
    has_efficient_algorithm: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_big_o": self.estimated_big_o,
            "score": round(self.score, 2),
            "max_score": self.max_score,
            "loop_depth": self.loop_depth,
            "has_recursion": self.has_recursion,
            "has_efficient_algorithm": self.has_efficient_algorithm,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EFFICIENT_ALGORITHMS = {
    "binary_search", "merge_sort", "quick_sort", "heap_sort",
    "dijkstra", "bfs", "dfs", "binary_search_tree",
}

COMPLEXITY_O1_SCORE = 1.0
COMPLEXITY_LOG_N_SCORE = 1.0
COMPLEXITY_N_SCORE = 0.9
COMPLEXITY_N_LOG_N_SCORE = 0.85
COMPLEXITY_N2_SCORE = 0.7
COMPLEXITY_N3_SCORE = 0.5
COMPLEXITY_N4_SCORE = 0.2
COMPLEXITY_DEFAULT_SCORE = 0.9


# ---------------------------------------------------------------------------
# Big-O Estimation
# ---------------------------------------------------------------------------
def estimate_complexity(features: ASTFeatures) -> ComplexityReport:
    """
    Estimate time complexity (Big-O) based on AST analysis.

    Uses a multi-factor approach:
    1. Loop nesting depth → base complexity
    2. Recursion detection → adjust for recursive algorithms
    3. Efficient algorithm override → downgrade complexity for known optimal algorithms
    4. Structural analysis → validate complexity estimate

    Args:
        features: AST analysis results

    Returns:
        ComplexityReport with estimated Big-O and normalized score
    """
    notes = []
    max_loop_depth = features.max_loop_depth
    has_recursion = features.has_recursion
    algorithms = set(features.algorithms)
    has_div2 = features.has_div2

    # Determine base complexity from loop depth and recursion
    big_o, score = _estimate_base_complexity(max_loop_depth, has_recursion, has_div2)

    # Efficient algorithm override: downgrade complexity for known optimal algorithms
    has_efficient = bool(algorithms & EFFICIENT_ALGORITHMS)
    if has_efficient:
        big_o, score, note = _apply_efficient_override(big_o, score, algorithms)
        if note:
            notes.append(note)

    # Add notes for specific patterns
    if has_recursion:
        notes.append("Recursion detected (depth contributing to complexity)")
    if max_loop_depth >= 3:
        notes.append(f"Deep nesting: {max_loop_depth} nested loops detected")

    return ComplexityReport(
        estimated_big_o=big_o,
        score=score,
        max_score=1.0,
        loop_depth=max_loop_depth,
        has_recursion=has_recursion,
        has_efficient_algorithm=has_efficient,
        notes=notes,
    )


def _estimate_base_complexity(
    max_loop_depth: int,
    has_recursion: bool,
    has_div2: bool,
) -> Tuple[str, float]:
    """
    Estimate base complexity from structural features.

    Returns:
        (big_o_string, normalized_score)
    """
    # O(log n) - single loop with division by 2 (binary search pattern)
    if max_loop_depth == 1 and has_div2:
        return "O(log n)", COMPLEXITY_LOG_N_SCORE

    # Pure recursion without loops
    if has_recursion and max_loop_depth == 0:
        return "O(recursion)", COMPLEXITY_LOG_N_SCORE

    # Recursion with loops (potentially exponential or bad recursion)
    if has_recursion and max_loop_depth >= 1:
        return "O(n^2)", COMPLEXITY_N2_SCORE

    # Loop depth based complexity
    depth_complexity_map = {
        0: ("O(1)", COMPLEXITY_O1_SCORE),
        1: ("O(n)", COMPLEXITY_N_SCORE),
        2: ("O(n^2)", COMPLEXITY_N2_SCORE),
        3: ("O(n^3)", COMPLEXITY_N3_SCORE),
    }

    # Default: 4+ loops = O(n^4) or worse
    if max_loop_depth >= 4:
        return f"O(n^{max_loop_depth})", COMPLEXITY_N4_SCORE

    return depth_complexity_map.get(max_loop_depth, ("O(n)", COMPLEXITY_N_SCORE))


def _apply_efficient_override(
    big_o: str,
    score: float,
    algorithms: set,
) -> Tuple[str, float, Optional[str]]:
    """
    Downgrade complexity estimate when efficient algorithms are detected.

    For example: if code has nested loops (O(n^2)) but uses merge_sort,
    the actual complexity might be O(n log n).

    Returns:
        (new_big_o, new_score, note)
    """
    note = None

    efficient_found = algorithms & EFFICIENT_ALGORITHMS
    if not efficient_found:
        return big_o, score, note

    algo_name = ", ".join(efficient_found)

    # Binary search: O(n^2) or O(n) → O(log n)
    if "binary_search" in efficient_found:
        if big_o in ("O(n^2)", "O(n^3)", "O(n)"):
            note = f"Efficient: {algo_name} → O(log n) optimal"
            return "O(log n)", COMPLEXITY_LOG_N_SCORE, note

    # Merge/Quick/Heap sort: O(n^2) → O(n log n)
    if {"merge_sort", "quick_sort", "heap_sort"} & efficient_found:
        if big_o in ("O(n^2)", "O(n^3)"):
            note = f"Efficient: {algo_name} → O(n log n)"
            return "O(n log n)", COMPLEXITY_N_LOG_N_SCORE, note

    # Dijkstra with heap: O(n^2) → O(n log n)
    if "dijkstra" in efficient_found:
        if big_o in ("O(n^2)", "O(n^3)"):
            note = f"Efficient: {algo_name} → O(n log n) with priority queue"
            return "O(n log n)", COMPLEXITY_N_LOG_N_SCORE, note

    # BFS/DFS: O(n^2) → O(n) or O(n log n)
    if {"bfs", "dfs"} & efficient_found:
        if big_o in ("O(n^2)", "O(n^3)"):
            note = f"Efficient: {algo_name} → O(n log n) typical"
            return "O(n log n)", COMPLEXITY_N_LOG_N_SCORE, note

    return big_o, score, note


# ---------------------------------------------------------------------------
# Complexity Curve Generation (for visualization)
# ---------------------------------------------------------------------------
def generate_complexity_curve(
    big_o: str,
    n_values: Optional[List[int]] = None,
    optimal_big_o: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate sample data points for complexity visualization.

    Creates (n, value) pairs for both student and optimal complexity,
    suitable for chart rendering.

    Args:
        big_o: Student's estimated complexity (e.g., "O(n^2)")
        n_values: Input size values to compute (default: [10, 20, 50, 100, 200, 500, 1000])
        optimal_big_o: Optimal complexity for this problem (e.g., "O(n log n)")

    Returns:
        Dict with student_curve, optimal_curve, and metadata
    """
    if n_values is None:
        n_values = [10, 20, 50, 100, 200, 500, 1000]

    student_curve = [_compute_complexity_value(big_o, n) for n in n_values]
    optimal_curve = []
    if optimal_big_o:
        optimal_curve = [_compute_complexity_value(optimal_big_o, n) for n in n_values]

    return {
        "n_values": n_values,
        "student_curve": {
            "big_o": big_o,
            "values": student_curve,
        },
        "optimal_curve": {
            "big_o": optimal_big_o or "N/A",
            "values": optimal_curve,
        } if optimal_curve else None,
        "metadata": {
            "description": "Complexity comparison chart data",
            "y_axis": "Relative operations count",
            "x_axis": "Input size (n)",
        },
    }


def _compute_complexity_value(big_o: str, n: int) -> float:
    """
    Compute the relative operations count for a given complexity and input size.

    Normalized to O(n) at n=100 = 100 operations.
    """
    import math

    if big_o == "O(1)":
        return 1.0
    elif big_o == "O(log n)":
        return round(math.log2(n) * 10, 2) if n > 0 else 0
    elif big_o == "O(n)":
        return float(n)
    elif big_o == "O(n log n)":
        return round(n * math.log2(n), 2) if n > 0 else 0
    elif big_o == "O(n^2)":
        return float(n * n) / 10  # Scale down for visualization
    elif big_o == "O(n^3)":
        return float(n * n * n) / 100  # Scale down more
    elif big_o.startswith("O(n^"):
        # Extract exponent
        try:
            exp = int(big_o.split("^")[1].rstrip(")"))
            return float(n ** exp) / (10 ** (exp - 1))
        except (ValueError, IndexError):
            return float(n)
    elif big_o == "O(recursion)":
        # Approximate as O(2^n) for naive recursion, capped
        return round(min(2 ** (n / 10), n * n * n), 2) if n > 0 else 0
    else:
        return float(n)  # Default to O(n)


# ---------------------------------------------------------------------------
# Scoring (for use in grading pipeline)
# ---------------------------------------------------------------------------
def score_complexity(features: ASTFeatures) -> Tuple[int, Optional[str]]:
    """
    Score complexity on a 0-10 scale.

    This is a convenience wrapper for the grading pipeline.
    Returns (score, note) tuple.

    Args:
        features: AST analysis results

    Returns:
        (score_out_of_10, descriptive_note)
    """
    report = estimate_complexity(features)

    # Map normalized score (0.0-1.0) to 0-10 scale
    score = round(report.score * 10)

    # Generate human-readable note
    if report.has_efficient_algorithm:
        note = f"Performance: {report.estimated_big_o} - optimal algorithm used"
    elif report.score >= 0.85:
        note = f"Performance: {report.estimated_big_o} - good"
    elif report.score >= 0.7:
        note = f"Performance: {report.estimated_big_o} - acceptable"
    elif report.score >= 0.5:
        note = f"Performance: {report.estimated_big_o} - could be improved"
    else:
        note = f"Performance: {report.estimated_big_o} - needs optimization"

    return score, note


__all__ = [
    "ASTFeatures",
    "ComplexityReport",
    "estimate_complexity",
    "score_complexity",
    "generate_complexity_curve",
    "EFFICIENT_ALGORITHMS",
]
