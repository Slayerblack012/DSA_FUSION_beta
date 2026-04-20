"""
DSA AutoGrader — Criteria Matcher.

Maps detected algorithms/data structures from AST analysis to rubric criteria
with precise 1-to-1 matching. Ensures grading is accurate and traceable.

Design:
  1. AST grader detects algorithms → produces a set of "detected capabilities"
  2. Criteria matcher maps capabilities → rubric criteria by keyword + semantic match
  3. Each matched criterion gets scored by the corresponding AST component
  4. Unmatched criteria are flagged as "not implemented"
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


logger = logging.getLogger("dsa.criteria_matcher")


# ============================================================
# Algorithm → Rubric keyword mappings
# ============================================================
# Each algorithm detected by AST has a set of Vietnamese keywords
# that may appear in rubric criteria names/descriptions.

_ALGORITHM_KEYWORDS: Dict[str, List[str]] = {
    # Basic data structures
    "List": ["danh sách", "list", "mảng", "array", "cấu trúc dữ liệu cơ bản"],
    "Tuple": ["bộ", "tuple", "bất biến", "immutable"],
    "Set": ["tập hợp", "set", "duy nhất", "unique", "không trùng"],
    "Dictionary": ["ánh xạ", "dictionary", "dict", "bảng băm", "hash map", "key-value"],
    "Generator/Yield": ["sinh", "generator", "yield", "lười biếng", "lazy"],
    "Lambda Function": ["lambda", "ẩn danh", "anonymous", "hàm gọn"],

    # Basic algorithms
    "Linear Search": ["tìm kiếm tuyến tính", "linear search", "duyệt", "tìm tuần tự"],
    "Basic Sorting (Bubble/Selection/Insertion)": [
        "sắp xếp", "sorting", "bubble", "selection", "insertion",
        "nổi bọt", "chèn", "đổi chỗ",
    ],

    # Intermediate
    "Linked List": ["danh sách liên kết", "linked list", "node", "con trỏ"],
    "Double Linked List": ["danh sách liên kết kép", "double linked", "prev", "next"],
    "Stack": ["ngăn xếp", "stack", "lifo", "push", "pop"],
    "Queue": ["hàng đợi", "queue", "fifo", "deque", "enqueue", "dequeue"],
    "Heap/Priority Queue": ["heap", "ưu tiên", "priority", "heapq"],
    "Binary Search": ["nhị phân", "binary search", "chia đôi", "tìm nhị phân"],

    # Advanced
    "Recursion": ["đệ quy", "recursion", "gọi lại chính nó"],
    "Divide & Conquer": ["chia để trị", "divide and conquer", "chia nhỏ"],
    "Quick Sort": ["quick sort", "sắp xếp nhanh", "pivot"],
    "Merge Sort": ["merge sort", "sắp xếp trộn", "trộn"],

    # Data structures
    "Binary Search Tree/BST": ["cây nhị phân", "bst", "binary search tree", "cây tìm kiếm"],
    "Trie (Prefix Tree)": ["trie", "tiền tố", "prefix tree", "từ điển"],
    "Graph": ["đồ thị", "graph", "cạnh", "đỉnh", "vertex", "edge", "adjacency"],

    # Advanced algorithms
    "Graph Traversal (BFS/DFS)": [
        "duyệt đồ thị", "bfs", "dfs", "breadth", "depth",
        "theo chiều rộng", "theo chiều sâu",
    ],
    "Dynamic Programming (DP)": [
        "quy hoạch động", "dynamic programming", "dp", "memo",
        "bảng phương án", "lưu trữ kết quả",
    ],
    "3D Dynamic Programming": ["quy hoạch động 3 chiều", "3d dp", "bảng 3 chiều"],
    "Backtracking": ["quay lui", "backtracking", "thử và sai", "undo"],
    "Dijkstra's Algorithm": ["dijkstra", "đường đi ngắn nhất", "shortest path"],
    "Greedy Algorithm": ["tham lam", "greedy", "tối ưu cục bộ"],
    "Matrix/Grid (BFS/DFS)": ["ma trận", "matrix", "grid", "bảng"],
}

# Fallback: generic criteria that always apply
_ALWAYS_APPLY_CRITERIA = [
    "kiểm thử", "test", "correct", "đúng", "chính xác", "output",
    "pep8", "style", "format", "readability", "coding convention",
    "trình bày", "định dạng",
]


@dataclass
class CriterionMatch:
    """Represents a single rubric criterion matched to detected algorithms."""
    criterion_name: str
    matched_algorithms: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 - 1.0
    max_score: float = 10.0
    source_text: str = ""
    description: str = ""
    criteria_code: str = ""


@dataclass
class MatchingResult:
    """Result of criteria matching for a single submission."""
    matched_criteria: List[CriterionMatch] = field(default_factory=list)
    unmatched_criteria: List[str] = field(default_factory=list)
    matched_exercise: Optional[Dict[str, str]] = None
    match_proof: Optional[Dict[str, Any]] = None


class CriteriaMatcher:
    """
    Matches detected AST algorithms to rubric criteria.

    Uses a two-phase approach:
    1. Keyword-based matching: Check if rubric criterion name/description
       contains keywords associated with detected algorithms.
    2. Semantic fallback: If no keyword match, check if the criterion
       is a generic one (testing, style, etc.) that always applies.
    """

    def __init__(self) -> None:
        self._keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, List[str]]:
        """Build reverse index: keyword → algorithm name."""
        index: Dict[str, List[str]] = {}
        for algo, keywords in _ALGORITHM_KEYWORDS.items():
            for kw in keywords:
                normalized = self._normalize(kw)
                if normalized not in index:
                    index[normalized] = []
                index[normalized].append(algo)
        return index

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison (handles Vietnamese diacritics)."""
        import unicodedata
        text = text.lower().strip()
        # Handle Vietnamese special characters that don't decompose properly
        text = text.replace('đ', 'd').replace('Đ', 'd')
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", text)

    def match(
        self,
        detected_algorithms: List[str],
        rubric_criteria: List[Dict[str, Any]],
        ast_breakdown: Dict[str, float],
        test_results: List[Dict[str, Any]],
    ) -> MatchingResult:
        """
        Match detected algorithms to rubric criteria.

        Args:
            detected_algorithms: List of algorithm names from AST grader
                (e.g. ["Binary Search", "Recursion", "List"])
            rubric_criteria: List of rubric criterion dicts from DB, each with:
                - name: str
                - description: str
                - max_score: float
            ast_breakdown: AST scoring breakdown dict
                (e.g. {"tests": 3.5, "dsa": 4.0, "pep8": 1.0, "complexity": 1.0})
            test_results: List of test case result dicts

        Returns:
            MatchingResult with matched/unmatched criteria
        """
        result = MatchingResult()

        algo_set = set(detected_algorithms)

        for criterion in rubric_criteria:
            name = criterion.get("name", "")
            description = criterion.get("description", "")
            max_score = criterion.get("max_score", 10.0)
            source_text = criterion.get("source_text", name)
            criteria_code = str(
                criterion.get("criteria_code")
                or criterion.get("criterion_code")
                or criterion.get("ma_tieu_chi")
                or ""
            ).strip()

            matched = self._match_single_criterion(
                name=name,
                description=description,
                detected_algorithms=algo_set,
                max_score=max_score,
                source_text=source_text,
                criteria_code=criteria_code,
            )

            if matched:
                result.matched_criteria.append(matched)
            else:
                result.unmatched_criteria.append(name)

        # If no rubric available, create generic criteria from AST breakdown
        if not rubric_criteria:
            result = self._create_default_criteria(
                detected_algorithms, ast_breakdown, test_results
            )

        return result

    def _match_single_criterion(
        self,
        name: str,
        description: str,
        detected_algorithms: Set[str],
        max_score: float,
        source_text: str,
        criteria_code: str,
    ) -> Optional[CriterionMatch]:
        """Try to match a single rubric criterion to detected algorithms."""
        name_norm = self._normalize(name)
        desc_norm = self._normalize(description)
        combined = f"{name_norm} {desc_norm}"

        matched_algos: List[str] = []
        best_confidence = 0.0

        # Phase 1: Check each detected algorithm's keywords against criterion text
        for algo in detected_algorithms:
            keywords = _ALGORITHM_KEYWORDS.get(algo, [])
            for kw in keywords:
                kw_norm = self._normalize(kw)
                if kw_norm in combined:
                    # Longer keywords = higher confidence (more specific match)
                    kw_length_score = len(kw_norm) / max(1, len(combined))
                    confidence = min(1.0, 0.5 + kw_length_score)
                    if confidence > best_confidence:
                        best_confidence = confidence
                    if algo not in matched_algos:
                        matched_algos.append(algo)
                    break  # One keyword match per algorithm is enough

        # Phase 2: Check if criterion is a generic one (always applies)
        if not matched_algos:
            for generic_kw in _ALWAYS_APPLY_CRITERIA:
                if self._normalize(generic_kw) in combined:
                    matched_algos = ["_generic"]
                    best_confidence = 0.6
                    break

        if not matched_algos:
            return None

        return CriterionMatch(
            criterion_name=name,
            matched_algorithms=matched_algos,
            confidence=best_confidence,
            max_score=max_score,
            source_text=source_text,
            description=description,
            criteria_code=criteria_code,
        )

    def _create_default_criteria(
        self,
        detected_algorithms: List[str],
        ast_breakdown: Dict[str, float],
        test_results: List[Dict[str, Any]],
    ) -> MatchingResult:
        """Create generic criteria when no rubric is available."""
        result = MatchingResult()

        # Always create test criterion
        test_passed = sum(1 for t in test_results if t.get("passed"))
        test_total = len(test_results)
        test_ratio = test_passed / test_total if test_total > 0 else 0
        result.matched_criteria.append(CriterionMatch(
            criterion_name="Kiểm thử (Testing)",
            matched_algorithms=["_test_execution"],
            confidence=1.0,
            max_score=4.0,
            description=f"Đạt {test_passed}/{test_total} test case",
        ))

        # DSA criterion if algorithms detected
        if detected_algorithms:
            result.matched_criteria.append(CriterionMatch(
                criterion_name="Cấu trúc dữ liệu & Thuật toán",
                matched_algorithms=detected_algorithms,
                confidence=0.8,
                max_score=6.0,
                description=f"Phát hiện: {', '.join(detected_algorithms)}",
            ))
        else:
            result.matched_criteria.append(CriterionMatch(
                criterion_name="Cấu trúc dữ liệu & Thuật toán",
                matched_algorithms=["_none"],
                confidence=0.0,
                max_score=6.0,
                description="Không phát hiện thuật toán đáng kể",
            ))

        return result

    def compute_scores(
        self,
        matching_result: MatchingResult,
        ast_breakdown: Dict[str, float],
        test_results: List[Dict[str, Any]],
        rubric_criteria: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute per-criterion scores based on matched algorithms.

        Returns list of dicts with:
        - criterion: str
        - earned: float
        - max: float
        - feedback: str
        - evidence: str
        """
        criteria_scores = []

        test_passed = sum(1 for t in test_results if t.get("passed"))
        test_total = len(test_results)
        test_ratio = test_passed / test_total if test_total > 0 else 0

        matched_name_set = set()

        for match in matching_result.matched_criteria:
            earned, feedback, evidence = self._score_criterion(
                match, ast_breakdown, test_ratio, test_results
            )
            matched_name_set.add(self._normalize(match.criterion_name))
            criteria_scores.append({
                "criterion": match.criterion_name,
                "earned": round(earned, 2),
                "max": round(match.max_score, 2),
                "feedback": feedback,
                "evidence": evidence,
                "source_text": match.source_text,
                "criteria_code": match.criteria_code,
            })

        # Preserve full DB rubric visibility: unmatched criteria are explicit with 0 score.
        for item in rubric_criteria or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("criteria_name") or "").strip()
            if not name:
                continue
            normalized_name = self._normalize(name)
            if normalized_name in matched_name_set:
                continue

            try:
                max_score = float(item.get("max_score") or 0)
            except (TypeError, ValueError):
                max_score = 0.0
            if max_score <= 0:
                continue

            criteria_scores.append({
                "criterion": name,
                "earned": 0.0,
                "max": round(max_score, 2),
                "feedback": "Chưa có bằng chứng triển khai tiêu chí này trong bài nộp.",
                "evidence": "Không tìm thấy dấu hiệu phù hợp trong AST/test results.",
                "source_text": item.get("source_text") or name,
                "criteria_code": item.get("criteria_code") or item.get("criterion_code") or "",
            })

        return criteria_scores

    def _score_criterion(
        self,
        match: CriterionMatch,
        ast_breakdown: Dict[str, float],
        test_ratio: float,
        test_results: List[Dict[str, Any]],
    ) -> Tuple[float, str, str]:
        """Score a single matched criterion. Returns (earned, feedback, evidence)."""
        algos = match.matched_algorithms

        # Generic test criterion
        if "_test_execution" in algos:
            earned = test_ratio * match.max_score
            feedback = f"Đạt {test_ratio:.0%} test case ({int(test_ratio * len(test_results))}/{len(test_results)})"
            failed_tests = [t for t in test_results if not t.get("passed")]
            if failed_tests:
                evidence = f"Sai ở: {', '.join(t.get('testcase_name', '?') for t in failed_tests[:3])}"
            else:
                evidence = "Tất cả test case đều đạt"
            return earned, feedback, evidence

        # Generic DSA criterion
        if "_generic" in algos or "_none" in algos:
            dsa_score = ast_breakdown.get("dsa", 0)
            max_dsa = 6.0
            ratio = dsa_score / max_dsa if max_dsa > 0 else 0
            earned = ratio * match.max_score
            if "_none" in algos:
                feedback = "Không phát hiện thuật toán hoặc cấu trúc dữ liệu đáng kể"
                evidence = "Code quá ngắn hoặc chỉ có cấu trúc cơ bản"
            else:
                feedback = "Đáp ứng tiêu chí chung về chất lượng code"
                evidence = f"AST breakdown: dsa={dsa_score}/{max_dsa}"
            return earned, feedback, evidence

        # Algorithm-specific criterion
        dsa_score = ast_breakdown.get("dsa", 0)
        max_dsa = 6.0
        algo_ratio = dsa_score / max_dsa if max_dsa > 0 else 0

        # Scale by match confidence
        earned = algo_ratio * match.max_score * match.confidence
        earned = min(earned, match.max_score)  # Cap at max

        algo_list = ", ".join(a for a in algos if not a.startswith("_"))
        feedback = f"Phát hiện thuật toán: {algo_list}"
        evidence = f"AST detected: {algo_list} | confidence={match.confidence:.2f}"

        # Add specifics from breakdown
        if ast_breakdown.get("pep8", 0) > 0:
            evidence += f" | PEP8={ast_breakdown['pep8']}"
        if ast_breakdown.get("complexity", 0) > 0:
            evidence += f" | complexity={ast_breakdown['complexity']}"

        return earned, feedback, evidence


# Singleton
criteria_matcher = CriteriaMatcher()
