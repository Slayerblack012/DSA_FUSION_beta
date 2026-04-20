"""
DSA AutoGrader - DSA & Complexity Scorer.

Scores code based on detected data structures, algorithms,
and time-complexity estimation.
"""

from typing import List, Optional, Tuple

from app.services.grading.constants import SCORING_CONSTANTS, CodeFeatures


class DSAScorer:
    """Scores code based on detected data structures and algorithms."""

    def __init__(self, features: CodeFeatures, code_lower: str, filename_lower: str) -> None:
        self.f = features
        self.code_lower = code_lower
        self.filename_lower = filename_lower
        self.algos: List[str] = []
        self.score = 0
        self.details: List[str] = []
        self.notes: List[str] = []

    def score_all(self) -> Tuple[int, str, List[str]]:
        """Score all aspects and return (score, algorithms, details)."""
        self._score_data_structures()
        self._score_basic_algorithms()
        self._score_intermediate_structures()
        self._score_intermediate_algorithms()
        self._score_advanced_structures()
        self._score_advanced_algorithms()
        self._check_structural_integrity()
        self._check_algorithm_mismatch()

        capped = min(SCORING_CONSTANTS.MAX_DSA_SCORE, self.score)
        algos_str = ", ".join(sorted(set(self.algos))) or "Cơ bản"
        return capped, algos_str, self.details

    def _add_score(self, points: int, algo_name: str, detail: str) -> None:
        """Add score and track algorithm."""
        self.algos.append(algo_name)
        self.score += points
        self.details.append(detail)

    def _check_structural_integrity(self) -> None:
        """Check if student implemented required data structures properly."""
        f = self.f

        # Linked List requires class
        if "linked" in self.filename_lower and not f.has_class:
            self.notes.append("Pedagogical requirement: Linked List assignment requires 'class Node'.")
            self.score = max(0, self.score - 2)
            self.details.append("SYSTEM: Penalty for not using Class for Linked List (-2 pts)")

        # Queue should use deque, not pop(0)
        if "queue" in self.filename_lower and not f.has_deque and "pop(0)" in self.code_lower:
            self.notes.append("Performance: Using pop(0) on list for Queue is O(n), use collections.deque O(1).")

        # Recursion check
        if any(x in self.filename_lower for x in ["recursion", "de_quy", "backtrack"]) and not f.has_recursion:
            self.notes.append("Wrong approach: This assignment requires recursion.")
            self.score = max(0, self.score - 2)
            self.details.append("SYSTEM: No recursion logic found (-2 pts)")

    def _score_data_structures(self) -> None:
        """Score basic data structures."""
        f = self.f
        sc = SCORING_CONSTANTS
        
        structure_scores = [
            (f.has_list, sc.SCORE_LIST, "List"),
            (f.has_tuple, sc.SCORE_TUPLE, "Tuple"),
            (f.has_set, sc.SCORE_SET, "Set"),
            (f.has_dict, sc.SCORE_DICT, "Dictionary"),
            (f.has_yield, sc.SCORE_YIELD, "Generator/Yield"),
            (f.has_lambda, sc.SCORE_LAMBDA, "Lambda Function"),
        ]
        
        for has_feature, score, name in structure_scores:
            if has_feature:
                self._add_score(score, name, f"{name} (+{score} pts)")

    def _score_basic_algorithms(self) -> None:
        """Score basic algorithms."""
        f = self.f
        sc = SCORING_CONSTANTS
        
        # Basic sorting (Bubble/Selection/Insertion)
        if f.has_nested_loops and f.has_swap:
            self._add_score(sc.SCORE_BASIC_ALGO, "Basic Sorting (Bubble/Selection/Insertion)",
                          f"Basic 2-loop sorting (+{sc.SCORE_BASIC_ALGO} pts)")
        # Linear search — only when no advanced structures present
        elif (
            f.loop_count > 0
            and f.if_count > 0
            and f.has_returns
            and not f.has_div2
            and not f.has_recursion
            and not f.has_nested_loops
            and not f.has_class  # not a data structure implementation
        ):
            self._add_score(sc.SCORE_BASIC_ALGO, "Linear Search", f"Linear Search (+{sc.SCORE_BASIC_ALGO} pts)")

    def _score_intermediate_structures(self) -> None:
        """Score intermediate data structures."""
        f = self.f
        sc = SCORING_CONSTANTS
        
        if f.has_class and "next" in f.class_attrs:
            if f.has_prev:
                 self._add_score(sc.SCORE_DOUBLE_LINKED_LIST, "Double Linked List", f"Double Linked List (+{sc.SCORE_DOUBLE_LINKED_LIST} pts)")
            else:
                 self._add_score(sc.SCORE_LINKED_LIST, "Linked List", f"Linked List (+{sc.SCORE_LINKED_LIST} pts)")

        if f.has_pop and not f.has_deque and not f.has_recursion:
            self._add_score(sc.SCORE_STACK, "Stack", f"Stack (+{sc.SCORE_STACK} pts)")

        if f.has_deque or (f.has_list and "pop(0)" in self.code_lower):
            self._add_score(sc.SCORE_QUEUE, "Queue", f"Queue (+{sc.SCORE_QUEUE} pts)")

        if "heapq" in f.imports:
            self._add_score(sc.SCORE_HEAP, "Heap/Priority Queue", f"Heap (+{sc.SCORE_HEAP} pts)")

    def _score_intermediate_algorithms(self) -> None:
        """Score intermediate algorithms.
        
        NOTE: Binary Search and Recursion/Divide&Conquer are mutually exclusive
        scoring paths to avoid double-counting.
        """
        f = self.f
        sc = SCORING_CONSTANTS
        
        # Binary search — only when NOT also doing recursion-based divide & conquer
        if f.has_div2 and f.has_while_loop and f.comparison_count > 0 and not f.has_recursion:
            self._add_score(sc.SCORE_BINARY_SEARCH, "Binary Search", f"Binary Search (divide by 2) (+{sc.SCORE_BINARY_SEARCH} pts)")

        # Recursion path (separate from iterative binary search)
        if f.has_recursion:
            self._add_score(sc.SCORE_RECURSION, "Recursion", f"Recursion (+{sc.SCORE_RECURSION} pts)")
            # Divide & Conquer only if recursion has 2+ recursive calls (true D&C pattern)
            if f.is_divide_conquer:
                self._add_score(sc.SCORE_DIVIDE_CONQUER, "Divide & Conquer", f"Divide & Conquer pattern (+{sc.SCORE_DIVIDE_CONQUER} pts)")
            self._score_sorting_algorithms()
        
        # Recursive binary search (has both div2 and recursion)
        elif f.has_div2 and f.has_recursion and f.comparison_count > 0:
            self._add_score(sc.SCORE_BINARY_SEARCH, "Binary Search (Recursive)", f"Binary Search recursive (+{sc.SCORE_BINARY_SEARCH} pts)")

    def _score_sorting_algorithms(self) -> None:
        """Analyze Quick Sort vs Merge Sort."""
        f = self.f
        sc = SCORING_CONSTANTS
        
        is_quick = f.has_list_comp_filter or (f.has_swap and f.loop_count > 0) or "pivot" in self.code_lower
        is_merge = f.has_slicing or "mid" in self.code_lower or "merge" in self.code_lower

        if is_quick and not is_merge:
            self._add_score(sc.SCORE_ADVANCED_SORT, "Quick Sort", f"Quick Sort (+{sc.SCORE_ADVANCED_SORT} pts)")
        elif is_merge:
            self._add_score(sc.SCORE_ADVANCED_SORT, "Merge Sort", f"Merge Sort (+{sc.SCORE_ADVANCED_SORT} pts)")
        elif "sort" in self.filename_lower:
            self._add_score(sc.SCORE_ADVANCED_SORT, "Advanced Sorting", f"Advanced Sorting (+{sc.SCORE_ADVANCED_SORT} pts)")

    def _score_advanced_structures(self) -> None:
        """Score advanced data structures."""
        f = self.f
        sc = SCORING_CONSTANTS
        
        if f.has_class and {"left", "right"}.issubset(f.class_attrs):
            self._add_score(sc.SCORE_BST, "Binary Search Tree/BST", f"BST/Tree (+{sc.SCORE_BST} pts)")

        if f.has_class and "children" in f.class_attrs:
            self._add_score(sc.SCORE_TRIE, "Trie (Prefix Tree)", f"Trie (+{sc.SCORE_TRIE} pts)")

        if "networkx" in f.imports or "adj" in f.class_attrs or "graph" in f.class_attrs:
            self._add_score(sc.SCORE_GRAPH, "Graph", f"Graph (+{sc.SCORE_GRAPH} pts)")

    def _score_advanced_algorithms(self) -> None:
        """Score advanced algorithms."""
        f = self.f
        sc = SCORING_CONSTANTS

        if f.has_dp_var and (f.has_nested_loops or f.has_recursion):
            self._add_score(sc.SCORE_DP, "Dynamic Programming (DP)", f"Dynamic Programming (+{sc.SCORE_DP} pts)")

        if (f.has_deque or f.has_recursion) and ("visit" in self.code_lower or "seen" in self.code_lower):
            self._add_score(sc.SCORE_BFS_DFS, "Graph Traversal (BFS/DFS)", f"BFS/DFS (+{sc.SCORE_BFS_DFS} pts)")

        if f.has_matrix_access and (f.has_recursion or f.has_deque):
            self._add_score(sc.SCORE_MATRIX, "Matrix/Grid (BFS/DFS)", f"Matrix (+{sc.SCORE_MATRIX} pts)")

        if f.has_3d_array_access and f.has_dp_var:
            self._add_score(sc.SCORE_DP_3D, "3D Dynamic Programming", f"3D DP (+{sc.SCORE_DP_3D} pts)")

        if f.has_recursion and f.loop_count > 0 and ("backtrack" in self.code_lower or "undo" in self.code_lower or f.has_pop):
            self._add_score(sc.SCORE_BACKTRACKING, "Backtracking", f"Backtracking (+{sc.SCORE_BACKTRACKING} pts)")

        if "heapq" in f.imports and any(x in self.code_lower for x in ["dist", "cost", "d[", "distance"]):
            self._add_score(sc.SCORE_DIJKSTRA, "Dijkstra's Algorithm", f"Dijkstra (+{sc.SCORE_DIJKSTRA} pts)")

        if f.has_greedy_pattern and f.loop_count > 0:
            self._add_score(sc.SCORE_GREEDY, "Greedy Algorithm", f"Greedy pattern detected (+{sc.SCORE_GREEDY} pts)")

    def _check_algorithm_mismatch(self) -> None:
        """Check if implemented algorithm matches expected (from filename)."""
        if self._expects_n_log_n_sort() and self._implemented_n_squared_sort():
            self._add_algorithm_mismatch_note("Quick/Merge Sort (O(n log n))", "Bubble/Insertion Sort (O(n^2))")
            self._penalize_wrong_algorithm()

        if self._expects_binary_search() and self._implemented_linear_search():
            self._add_algorithm_mismatch_note("Binary Search (divide and conquer)", "Linear Search (sequential)")
            self._penalize_wrong_algorithm()

    def _expects_n_log_n_sort(self) -> bool:
        return any(x in self.filename_lower for x in ["quick", "merge", "heap"]) and "sort" in self.filename_lower

    def _implemented_n_squared_sort(self) -> bool:
        return not self.f.has_recursion and self.f.has_nested_loops

    def _expects_binary_search(self) -> bool:
        return "binary" in self.filename_lower and "search" in self.filename_lower

    def _implemented_linear_search(self) -> bool:
        return not self.f.has_div2 and self.f.loop_count > 0

    def _add_algorithm_mismatch_note(self, expected: str, actual: str) -> None:
        self.notes.append(f"Algorithm mismatch: Expected {expected} but implemented {actual}.")

    def _penalize_wrong_algorithm(self) -> None:
        penalty = SCORING_CONSTANTS.WRONG_ALGORITHM_PENALTY
        self.score = max(0, self.score - penalty)
        self.details.append(f"PENALTY: Wrong algorithm (-{penalty} pts)")


def score_complexity(features: CodeFeatures) -> Tuple[int, Optional[str]]:
    """Score based on time-complexity (Big-O).

    Scoring logic (educational):
    - O(log n)       → 10/10  (binary search, optimal)
    - O(n)           → 10/10  (single loop, good)
    - O(n log n)     → 9/10   (merge/quick sort, acceptable)
    - O(n²)          → 8/10   (nested loops, average)
    - O(n³)          → 5/10   (triple nested, slow)
    - O(n⁴+)         → 2/10   (too slow)
    - Recursion only → depends on pattern:
        - D&C (2+ recursive calls, no extra loops) → 9/10 (likely O(n log n))
        - Recursion + loops                        → 7/10 (could be O(n²) or worse)
        - Single recursion (no loops)              → 10/10 (likely O(n))
    """
    max_loop_depth = features.max_loop_depth

    # O(log n) — iterative binary search (div by 2 in a loop, no recursion)
    if max_loop_depth == 1 and features.has_div2 and not features.has_recursion:
        return (SCORING_CONSTANTS.COMPLEXITY_DEFAULT_SCORE, "Performance: O(log n) optimal (10/10 pts)")

    # Recursion-based complexity
    if features.has_recursion:
        if features.is_divide_conquer and max_loop_depth == 0:
            # True D&C (Merge Sort, Quick Sort) → O(n log n)
            return (9, "Performance: O(n log n) divide & conquer (9/10 pts)")
        if max_loop_depth >= 2:
            # Recursion + nested loops → likely O(n² log n) or worse
            return (SCORING_CONSTANTS.COMPLEXITY_O_N2_SCORE, "Performance: Recursion with nested loops may be O(n² log n) (8/10 pts)")
        if max_loop_depth >= 1:
            # Recursion + single loop → O(n log n) or O(n²)
            return (SCORING_CONSTANTS.COMPLEXITY_O_N2_SCORE, "Performance: Recursion with loop, check complexity (8/10 pts)")
        # Pure recursion, single call per level → O(n)
        return (SCORING_CONSTANTS.COMPLEXITY_DEFAULT_SCORE, "Performance: O(n) linear recursion (10/10 pts)")

    # Loop depth scoring
    complexity_scores = {
        4: (SCORING_CONSTANTS.COMPLEXITY_O_N4_SCORE, f"Poor performance: O(n^{max_loop_depth}) complexity is too high (2/10 pts)"),
        3: (SCORING_CONSTANTS.COMPLEXITY_O_N3_SCORE, "Performance: O(n^3) complexity is quite slow (5/10 pts)"),
        2: (SCORING_CONSTANTS.COMPLEXITY_O_N2_SCORE, "Performance: O(n^2) average (8/10 pts)"),
    }

    if max_loop_depth in complexity_scores:
        return complexity_scores[max_loop_depth]

    return (SCORING_CONSTANTS.COMPLEXITY_DEFAULT_SCORE, "Performance: O(n) good (10/10 pts)")
