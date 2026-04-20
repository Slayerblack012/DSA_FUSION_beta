"""
DSA AutoGrader - Test Runner.

Static code checks and dynamic test-case execution.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.grading.constants import SCORING_CONSTANTS, CodeFeatures
from app.services.testcase_loader import get_test_cases
from app.utils.sandbox import run_python_sandbox

# ═══════════════════════════════════════════
#  Static Test Score
# ═══════════════════════════════════════════


def score_static_tests(features: CodeFeatures) -> int:
    """Score based on static code features (before running tests)."""
    score = 0
    if features.has_main_guard:
        score += SCORING_CONSTANTS.MAIN_GUARD_BONUS
    if features.has_returns or "print" in features.nodes_for_fingerprint:
        score += SCORING_CONSTANTS.RETURN_OR_PRINT_BONUS
    if features.has_type_hints:
        score += SCORING_CONSTANTS.TYPE_HINT_BONUS
    return score


# ═══════════════════════════════════════════
#  Dynamic Test Runner
# ═══════════════════════════════════════════


def run_dynamic_tests(
    code: str,
    filename: str,
    topic: Optional[str],
) -> Tuple[int, List[str], List[Dict]]:
    """Run test cases and return (score, notes, test_results)."""
    from app.utils.sandbox import run_python_sandbox_batch
    
    test_cases = get_test_cases(topic)
    if not test_cases:
        return 0, [], []

    # Prepare batch execution
    inputs = [tc["input"] for tc in test_cases]
    timeout = _get_test_timeout(filename)
    
    # Run all test cases in ONE process instead of many (Massive performance boost)
    batch_results = run_python_sandbox_batch(code, inputs, timeout_per_case=timeout)
    
    notes = [f"--- Running {len(test_cases)} test cases in batch mode ---"]
    passed = 0
    test_results = []

    for i, tc in enumerate(test_cases):
        result = batch_results[i] if i < len(batch_results) else None
        if not result:
            continue
            
        actual = result.output.strip() if result.output else ""
        expected = tc["expected"]
        is_passed = result.success and actual == expected

        # Store detailed results
        test_results.append({
            "testcase_id": tc.get("id", tc["name"]),
            "testcase_name": tc["name"],
            "input": tc["input"],
            "expected_output": expected,
            "actual_output": actual,
            "error": result.error if not result.success else "",
            "time_ms": round(result.time_used * 1000, 2),
            "memory_kb": round(result.memory_used, 2),
            "passed": is_passed,
            "timeout": result.timeout,
            "runtime_error": not result.success and not result.timeout
        })

        if is_passed:
            passed += 1
            if len(test_cases) <= 5: # Only log individual successes for small batches
                notes.append(f"✓ {tc['name']}: PASSED")
        elif not result.success:
            notes.append(_format_runtime_error(tc, result))
            # In batch mode, we continue to see if other tests pass, 
            # unless it was a fatal process crash (which sandbox handles)
        else:
            notes.append(_format_wrong_output(tc, result))

    max_score = SCORING_CONSTANTS.MAX_TEST_SCORE
    score = int((passed / len(test_cases)) * max_score) if test_cases else 0
    notes.append(f"Test result: {passed}/{len(test_cases)} test cases passed")
    return score, notes, test_results


# ═══════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════


def _get_test_timeout(filename: str) -> int:
    """Get test timeout based on problem complexity."""
    complex_problems = [
        "graph",
        "bfs",
        "dfs",
        "nqueen",
        "backtrack",
        "mst",
        "matrix",
    ]
    if any(k in filename.lower() for k in complex_problems):
        return SCORING_CONSTANTS.TEST_TIMEOUT_COMPLEX
    return SCORING_CONSTANTS.TEST_TIMEOUT_NORMAL


def _format_runtime_error(tc: Dict, result: Any) -> str:
    """Format runtime error message."""
    err_msg = result.error if hasattr(result, 'error') else "Unknown Error"
    line_match = re.search(r"line (\d+)", err_msg)
    line_info = f" at line {line_match.group(1)}" if line_match else ""
    err_type = err_msg.split("\n")[-1] if err_msg else "Unknown Error"
    return f"Runtime error{line_info} ({tc['name']}): {err_type}"


def _format_wrong_output(tc: Dict, result: Any) -> str:
    """Format wrong output message."""
    inp_short = tc["input"].replace("\n", " ")
    if len(inp_short) > 20:
        inp_short = inp_short[:20] + "..."

    actual = result.output.strip() if hasattr(result, 'output') else ""
    return (
        f"Wrong output at '{tc['name']}' (Input: {inp_short}): "
        f"Expected '{tc['expected']}', but got '{actual}'"
    )
