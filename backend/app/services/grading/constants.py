"""
DSA AutoGrader - Scoring Constants & Data Classes.

Centralised configuration for all grading scores.
No magic numbers elsewhere in the grading pipeline!
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

# ═══════════════════════════════════════════
#  Scoring Constants
# ═══════════════════════════════════════════


class SCORING_CONSTANTS:
    """Centralised scoring configuration — No magic numbers!"""

    # Maximum scores (10-point scale)
    MAX_PEP8_SCORE = 1
    MAX_DSA_SCORE = 6
    MAX_COMPLEXITY_SCORE = 1
    MAX_TEST_SCORE = 4
    MAX_TOTAL_SCORE = 10

    # PEP8 penalties
    PEP8_TAB_PENALTY = 2
    PEP8_LINE_LENGTH = 79
    PEP8_MAX_LINE_DEDUCTION = 4
    PEP8_LINES_PER_DEDUCTION = 5
    PEP8_SPAGHETTI_PENALTY = 2

    # Code quality thresholds
    FUNCTION_MAX_LINES = 30
    GLOBAL_VARS_THRESHOLD = 5
    MIN_CODE_NODES = 10
    MAX_SCORE_FOR_SHORT_CODE = 30

    # Complexity scores
    COMPLEXITY_O_N4_SCORE = 2
    COMPLEXITY_O_N3_SCORE = 5
    COMPLEXITY_O_N2_SCORE = 8
    COMPLEXITY_DEFAULT_SCORE = 10

    # Test scoring
    TEST_TIMEOUT_NORMAL = 2
    TEST_TIMEOUT_COMPLEX = 5
    MAIN_GUARD_BONUS = 0.5
    TYPE_HINT_BONUS = 0.5
    RETURN_OR_PRINT_BONUS = 1

    # Algorithm detection penalties
    WRONG_ALGORITHM_PENALTY = 1

    # DSA component scores (weighted for 6.0 max)
    SCORE_LIST = 0.2
    SCORE_TUPLE = 0.2
    SCORE_SET = 0.3
    SCORE_DICT = 0.3
    SCORE_YIELD = 0.5
    SCORE_LAMBDA = 0.5
    
    SCORE_BASIC_ALGO = 2.0
    SCORE_LINKED_LIST = 1.5
    SCORE_STACK = 0.5
    SCORE_QUEUE = 1.0
    SCORE_HEAP = 1.5
    SCORE_BINARY_SEARCH = 3.0
    SCORE_RECURSION = 1.0
    SCORE_ADVANCED_SORT = 1.0
    SCORE_BST = 2.0
    SCORE_TRIE = 2.5
    SCORE_GRAPH = 2.0
    SCORE_DP = 2.5
    SCORE_BFS_DFS = 2.0
    SCORE_MATRIX = 2.0
    SCORE_DP_3D = 3.0
    SCORE_BACKTRACKING = 3.0
    SCORE_DIJKSTRA = 2.5
    SCORE_GREEDY = 2.0
    SCORE_DIVIDE_CONQUER = 2.0
    SCORE_DOUBLE_LINKED_LIST = 2.0

    # Confidence score
    DEFAULT_CONFIDENCE = 80


# ═══════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════


@dataclass
class CodeFeatures:
    """Stores extracted AST features for analysis."""

    # Data structures
    has_list: bool = False
    has_tuple: bool = False
    has_set: bool = False
    has_dict: bool = False

    # Control flow
    has_nested_loops: bool = False
    has_swap: bool = False
    has_recursion: bool = False
    has_class: bool = False
    has_div2: bool = False
    has_pop: bool = False
    has_deque: bool = False
    has_dp_var: bool = False
    has_while_loop: bool = False
    has_main_guard: bool = False
    has_type_hints: bool = False
    has_yield: bool = False
    has_lambda: bool = False
    has_slicing: bool = False
    has_list_comp_filter: bool = False
    has_matrix_access: bool = False
    has_3d_array_access: bool = False
    has_returns: bool = False

    # Advanced Detection
    has_prev: bool = False
    has_greedy_pattern: bool = False
    is_divide_conquer: bool = False
    has_binary_op: bool = False

    # Counters
    loop_count: int = 0
    if_count: int = 0
    comparison_count: int = 0
    global_var_count: int = 0
    long_func_count: int = 0
    node_count: int = 0

    # Collections
    imports: Set[str] = field(default_factory=set)
    class_attrs: Set[str] = field(default_factory=set)
    nodes_for_fingerprint: List[str] = field(default_factory=list)

    # Complexity
    max_nesting: int = 0
    max_loop_depth: int = 0


@dataclass
class ASTGradingResult:
    """Stores final AST grading result."""

    filename: str
    total_score: float
    breakdown: Dict[str, float]
    algorithms: str
    runtime: str
    status: str
    valid_score: bool
    confidence: int
    fingerprint: Set
    notes: List[str]
