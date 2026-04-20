"""
DSA AutoGrader - Batch Test Runner.

Run multiple test cases efficiently in a single sandboxed process.
Unlike the simple test_runner which runs one test at a time,
this runner batches all test cases together for performance.

Features:
- All test cases in single subprocess (fast)
- Memory monitoring per batch
- Timeout enforcement (total + per-case)
- Fail-fast mode (stop on first error) or full-run mode
- Detailed per-case results with memory/time tracking
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.core.config import SANDBOX_MAX_CPU_TIME, SANDBOX_MAX_MEMORY_MB
from app.utils.sandbox import SandboxResult, run_python_sandbox_batch

logger = logging.getLogger("dsa.batch_test_runner")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class TestCaseResult:
    """Result of a single test case."""
    test_id: str
    input_data: str
    expected_output: str
    actual_output: str = ""
    passed: bool = False
    runtime_error: str = ""
    timed_out: bool = False
    execution_time_ms: float = 0.0
    memory_usage_kb: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "passed": self.passed,
            "expected": self.expected_output[:200],
            "actual": self.actual_output[:200],
            "runtime_error": self.runtime_error,
            "timed_out": self.timed_out,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "memory_usage_kb": self.memory_usage_kb,
            "notes": self.notes,
        }


@dataclass
class BatchTestReport:
    """Complete batch test execution report."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    timed_out: int = 0
    score: float = 0.0  # Normalized 0.0 - 1.0 (or scaled to max_score)
    max_score: float = 4.0
    total_time_ms: float = 0.0
    peak_memory_kb: int = 0
    results: List[TestCaseResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    fail_fast_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "timed_out": self.timed_out,
            "score": round(self.score, 2),
            "max_score": self.max_score,
            "pass_rate": round(self.passed / self.total * 100, 1) if self.total > 0 else 0,
            "total_time_ms": round(self.total_time_ms, 2),
            "peak_memory_kb": self.peak_memory_kb,
            "fail_fast_triggered": self.fail_fast_triggered,
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Test Case Data
# ---------------------------------------------------------------------------
@dataclass
class TestCase:
    """A single test case with input and expected output."""
    id: str
    input_data: str
    expected_output: str
    name: str = ""


def load_test_cases(
    testcase_root: str,
    topic: str,
    max_cases: int = 10,
) -> List[TestCase]:
    """
    Load test cases from the filesystem.

    Supports both naming conventions:
    - {id}.input / {id}.output
    - input_{id}.txt / output_{id}.txt

    Args:
        testcase_root: Root directory for test cases
        topic: Topic subdirectory (e.g., "fibonacci", "sort")
        max_cases: Maximum number of test cases to load

    Returns:
        List of TestCase objects
    """
    import os

    topic_dir = os.path.join(testcase_root, topic)
    if not os.path.isdir(topic_dir):
        logger.warning("Test case directory not found: %s", topic_dir)
        return []

    test_cases = []
    for i in range(1, max_cases + 1):
        # Try both naming conventions
        input_path = None
        output_path = None

        # Convention 1: {id}.input / {id}.output
        alt_input = os.path.join(topic_dir, f"{i}.input")
        alt_output = os.path.join(topic_dir, f"{i}.output")
        if os.path.exists(alt_input) and os.path.exists(alt_output):
            input_path = alt_input
            output_path = alt_output

        # Convention 2: input_{id}.txt / output_{id}.txt
        std_input = os.path.join(topic_dir, f"input_{i}.txt")
        std_output = os.path.join(topic_dir, f"output_{i}.txt")
        if os.path.exists(std_input) and os.path.exists(std_output):
            input_path = std_input
            output_path = std_output

        if input_path and output_path:
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    input_data = f.read().strip()
                with open(output_path, "r", encoding="utf-8") as f:
                    expected_output = f.read().strip()

                test_cases.append(TestCase(
                    id=str(i),
                    input_data=input_data,
                    expected_output=expected_output,
                    name=f"Test {i}",
                ))
            except Exception as e:
                logger.warning("Failed to load test case %s: %s", i, e)
        else:
            # Stop at first missing case (assumes sequential numbering)
            break

    logger.info("Loaded %d test cases for topic: %s", len(test_cases), topic)
    return test_cases


# ---------------------------------------------------------------------------
# Batch Test Runner
# ---------------------------------------------------------------------------
class BatchTestRunner:
    """
    Batch test runner for efficient test execution.

    Runs all test cases in a single sandboxed subprocess for performance,
    with detailed tracking of time, memory, and pass/fail per case.

    Usage:
        runner = BatchTestRunner()
        report = runner.run_batch(code, test_cases, topic="fibonacci")
    """

    def __init__(
        self,
        timeout_per_case: int = None,
        max_memory_mb: int = None,
        max_score: float = 4.0,
        fail_fast: bool = False,
    ):
        """
        Initialize batch test runner.

        Args:
            timeout_per_case: Timeout per test case in seconds
            max_memory_mb: Maximum memory allowed in MB
            max_score: Maximum score for passing all tests
            fail_fast: Stop on first runtime error (True) or run all tests (False)
        """
        self.timeout_per_case = timeout_per_case or SANDBOX_MAX_CPU_TIME
        self.max_memory_mb = max_memory_mb or SANDBOX_MAX_MEMORY_MB
        self.max_score = max_score
        self.fail_fast = fail_fast

    def run_batch(
        self,
        code: str,
        test_cases: List[TestCase],
        topic: str = "",
    ) -> BatchTestReport:
        """
        Run all test cases in batch mode.

        Args:
            code: Student's Python source code
            test_cases: List of test cases to run
            topic: Topic name (for logging/complexity detection)

        Returns:
            BatchTestReport with detailed results
        """
        report = BatchTestReport(
            total=len(test_cases),
            max_score=self.max_score,
        )

        if not test_cases:
            report.errors.append("No test cases provided")
            return report

        # Detect if topic needs longer timeout
        is_complex = self._is_complex_topic(topic)
        effective_timeout = self.timeout_per_case
        if is_complex:
            effective_timeout = max(self.timeout_per_case, 10)
            logger.info("Complex topic detected: extending timeout to %ds", effective_timeout)

        # Run all test cases in batch
        inputs = [tc.input_data for tc in test_cases]

        start_time = time.time()
        try:
            sandbox_results = run_python_sandbox_batch(
                code=code,
                inputs=inputs,
                timeout_per_case=effective_timeout,
                max_memory_mb=self.max_memory_mb,
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            report.total_time_ms = elapsed
            report.errors.append(f"Sandbox execution failed: {str(e)}")
            logger.error("Sandbox batch execution failed: %s", e)
            return report

        elapsed = (time.time() - start_time) * 1000
        report.total_time_ms = elapsed

        # Process results
        peak_memory = 0
        for i, (tc, sr) in enumerate(zip(test_cases, sandbox_results)):
            result = self._process_sandbox_result(tc, sr, i + 1)
            report.results.append(result)

            if result.passed:
                report.passed += 1
            else:
                report.failed += 1
                if result.timed_out:
                    report.timed_out += 1

            if sr.memory_usage_kb:
                peak_memory = max(peak_memory, sr.memory_usage_kb)

            # Fail-fast: stop if runtime error (not timeout)
            if self.fail_fast and result.runtime_error and not result.timed_out:
                report.fail_fast_triggered = True
                # Fill remaining test cases as "not run"
                for j in range(i + 1, len(test_cases)):
                    report.results.append(TestCaseResult(
                        test_id=test_cases[j].id,
                        input_data=test_cases[j].input_data,
                        expected_output=test_cases[j].expected_output,
                        notes="Not run (fail-fast triggered)",
                    ))
                    report.failed += 1
                break

        report.peak_memory_kb = peak_memory

        # Calculate score
        if report.total > 0:
            pass_ratio = report.passed / report.total
            report.score = pass_ratio * self.max_score

        logger.info(
            "Batch test results: %d/%d passed (score: %.1f/%.1f, time: %.0fms)",
            report.passed, report.total,
            report.score, self.max_score,
            report.total_time_ms,
        )

        return report

    @staticmethod
    def _is_complex_topic(topic: str) -> bool:
        """Check if topic typically needs longer execution time."""
        complex_keywords = {
            "graph", "bfs", "dfs", "dijkstra", "nqueen", "backtrack",
            "mst", "matrix", "dynamic_programming", "dp",
        }
        topic_lower = topic.lower()
        return any(kw in topic_lower for kw in complex_keywords)

    @staticmethod
    def _process_sandbox_result(
        tc: TestCase,
        sr: SandboxResult,
        index: int,
    ) -> TestCaseResult:
        """Convert a sandbox result to a TestCaseResult."""
        # Normalize outputs for comparison
        actual = sr.output.strip() if sr.output else ""
        expected = tc.expected_output.strip()

        # Compare outputs (allow minor whitespace differences)
        passed = actual.replace("\r\n", "\n") == expected.replace("\r\n", "\n")

        return TestCaseResult(
            test_id=tc.id,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            actual_output=actual[:500],  # Truncate long outputs
            passed=passed,
            runtime_error=sr.error or "",
            timed_out=sr.timed_out,
            execution_time_ms=sr.execution_time_ms,
            memory_usage_kb=sr.memory_usage_kb,
            notes=f"Test {index}: {'PASSED' if passed else 'FAILED'}",
        )

    def run_from_directory(
        self,
        code: str,
        testcase_root: str,
        topic: str,
        max_cases: int = 10,
    ) -> BatchTestReport:
        """
        Convenience method: load test cases from directory and run.

        Args:
            code: Student's Python source code
            testcase_root: Root directory for all test cases
            topic: Subdirectory for this specific topic
            max_cases: Maximum number of test cases to load

        Returns:
            BatchTestReport with detailed results
        """
        test_cases = load_test_cases(testcase_root, topic, max_cases)
        if not test_cases:
            return BatchTestReport(
                total=0,
                errors=[f"No test cases found for topic: {topic}"],
            )

        return self.run_batch(code, test_cases, topic)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------
def run_batch_tests(
    code: str,
    test_cases: List[TestCase],
    topic: str = "",
    max_score: float = 4.0,
    fail_fast: bool = False,
) -> BatchTestReport:
    """
    Run batch tests with default settings.

    Args:
        code: Student's Python source code
        test_cases: List of test cases
        topic: Topic name
        max_score: Maximum score
        fail_fast: Stop on first error

    Returns:
        BatchTestReport
    """
    runner = BatchTestRunner(max_score=max_score, fail_fast=fail_fast)
    return runner.run_batch(code, test_cases, topic)


def run_batch_from_directory(
    code: str,
    testcase_root: str,
    topic: str,
    max_cases: int = 10,
    max_score: float = 4.0,
    fail_fast: bool = False,
) -> BatchTestReport:
    """
    Run batch tests loading test cases from filesystem.

    Args:
        code: Student's Python source code
        testcase_root: Root test case directory
        topic: Topic subdirectory
        max_cases: Max test cases to load
        max_score: Maximum score
        fail_fast: Stop on first error

    Returns:
        BatchTestReport
    """
    runner = BatchTestRunner(max_score=max_score, fail_fast=fail_fast)
    return runner.run_from_directory(code, testcase_root, topic, max_cases)


__all__ = [
    "TestCase",
    "TestCaseResult",
    "BatchTestReport",
    "BatchTestRunner",
    "load_test_cases",
    "run_batch_tests",
    "run_batch_from_directory",
]
