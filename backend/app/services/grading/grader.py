"""
DSA AutoGrader - Main AST Grader (Orchestrator).

Coordinates all scoring components:
  PEP8 → AST extraction → DSA scoring → Complexity →
  Spaghetti check → Dynamic tests → Final result.
"""

import ast
import time
from typing import Dict, List, Set

from app.services.grading.constants import SCORING_CONSTANTS
from app.services.grading.extractor import ASTFeatureExtractor
from app.services.grading.pep8_checker import apply_spaghetti_penalties, check_pep8
from app.services.grading.scorer import DSAScorer, score_complexity
from app.services.grading.test_runner import run_dynamic_tests
from app.utils.security import check_python_safety


def _create_safety_failure_result(filename: str, violations: List[Dict]) -> Dict:
    """Create result for code that fails safety check."""
    formatted_violations = [
        v["message"] if isinstance(v, dict) and "message" in v else str(v)
        for v in violations
    ]
    return {
        "filename": filename,
        "total_score": 0,
        "breakdown": {"pep8": 0, "dsa": 0, "complexity": 0, "tests": 0},
        "algorithms": "Bị từ chối",
        "runtime": "0ms",
        "status": "FLAG",
        "valid_score": False,
        "notes": ["PHÁT HIỆN MÃ NGUY HIỂM:"] + formatted_violations,
    }


def _create_syntax_error_result(filename: str, error: SyntaxError, runtime_ms: float) -> Dict:
    """Create result for code with syntax errors."""
    return {
        "filename": filename,
        "total_score": 0.0,
        "breakdown": {"pep8": 0, "dsa": 0, "complexity": 0, "tests": 0},
        "algorithms": "",
        "runtime": f"{runtime_ms:.0f}ms",
        "status": "WA",
        "valid_score": False,
        "confidence": 0,
        "notes": [f"Syntax error: {error.msg} at line {error.lineno}"],
    }


def generate_fingerprint(nodes: List[str]) -> Set:
    """Generate AST n-gram fingerprint for plagiarism detection."""
    if len(nodes) < 3:
        return set(nodes)
    return set(tuple(nodes[i : i + 3]) for i in range(len(nodes) - 2))


class DSALightningGrader:
    """Main grader — coordinates all scoring components."""

    def grade_file_ultra_fast(self, code: str, filename: str, topic: str = None) -> Dict:
        """Grade a Python file using AST analysis and dynamic testing."""
        start_time = time.time()
        code_lower = code.lower()
        filename_lower = filename.lower()

        # Step 1: Safety check
        safety_violations = check_python_safety(code)
        if safety_violations:
            return _create_safety_failure_result(filename, safety_violations)

        # Step 2: Syntax validation
        try:
            tree = ast.parse(code, filename or "<string>")
        except SyntaxError as e:
            return _create_syntax_error_result(filename, e, (time.time() - start_time) * 1000)

        # Step 3: Extract AST features
        extractor = ASTFeatureExtractor()
        features = extractor.extract(tree)

        # Step 4-8: Score all components
        scorer = DSAScorer(features, code_lower, filename_lower)
        dsa_score, algorithms, dsa_details = scorer.score_all()
        notes = scorer.notes

        pep8_score, pep8_notes = check_pep8(code)
        notes.extend(pep8_notes)

        complexity_score, complexity_note = score_complexity(features)
        if complexity_note:
            notes.append(complexity_note)

        pep8_score, spaghetti_notes = apply_spaghetti_penalties(pep8_score, features)
        notes.extend(spaghetti_notes)

        test_score, test_notes, test_results = run_dynamic_tests(code, filename, topic)
        notes.extend(test_notes)

        # Step 9: Calculate final score
        raw_total = pep8_score + dsa_score + complexity_score + test_score
        total_score = self._calculate_final_score(raw_total, features.node_count)

        # Step 10-11: Generate fingerprint and build result
        # Determine status: TLE if any test timed out, FLAG already handled above
        has_tle = any(t.get("timeout") for t in test_results)
        fingerprint = generate_fingerprint(features.nodes_for_fingerprint)
        return self._build_result(
            filename=filename,
            total_score=total_score,
            pep8_score=pep8_score,
            dsa_score=dsa_score,
            complexity_score=complexity_score,
            test_score=test_score,
            algorithms=algorithms,
            dsa_details=dsa_details,
            runtime_ms=(time.time() - start_time) * 1000,
            fingerprint=fingerprint,
            notes=notes,
            test_results=test_results,
            has_tle=has_tle,
        )

    def _calculate_final_score(self, raw_total: float, node_count: int) -> float:
        """Calculate final score with anti-gaming adjustments."""
        if node_count < SCORING_CONSTANTS.MIN_CODE_NODES:
            return min(raw_total, SCORING_CONSTANTS.MAX_SCORE_FOR_SHORT_CODE)
        return round(min(SCORING_CONSTANTS.MAX_TOTAL_SCORE, raw_total), 1)

    def _build_result(self, **kwargs) -> Dict:
        """Build final grading result dictionary."""
        fingerprint = kwargs["fingerprint"]
        if isinstance(fingerprint, (set, frozenset)):
            fingerprint = [
                list(item) if isinstance(item, tuple) else item
                for item in fingerprint
            ]

        has_tle = kwargs.get("has_tle", False)
        total_score = kwargs["total_score"]
        if has_tle:
            status = "TLE"
        elif total_score >= 5:
            status = "AC"
        else:
            status = "WA"

        return {
            "filename": kwargs["filename"],
            "total_score": total_score,
            "breakdown": {
                "pep8": round(kwargs["pep8_score"], 1),
                "dsa": kwargs["dsa_score"],
                "complexity": kwargs["complexity_score"],
                "tests": kwargs["test_score"],
            },
            "algorithms": kwargs["algorithms"],
            "runtime": f"{kwargs['runtime_ms']:.0f}ms",
            "runtime_ms": kwargs["runtime_ms"],
            "status": status,
            "valid_score": True,
            "confidence": SCORING_CONSTANTS.DEFAULT_CONFIDENCE,
            "fingerprint": fingerprint,
            "notes": self._format_notes(kwargs["notes"], kwargs["dsa_details"]),
            "test_results": kwargs.get("test_results", []),
        }

    def _format_notes(self, notes: List[str], dsa_details: List[str]) -> List[str]:
        """Format notes with DSA explanation at the top."""
        if dsa_details:
            explanation = f"Detected algorithms: {', '.join(dsa_details)}"
            return [explanation] + notes
        return notes


# Singleton instance for reuse
lightning_grader = DSALightningGrader()
