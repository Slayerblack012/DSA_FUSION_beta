"""
DSA AutoGrader - AI Token Usage Analyzer.

Measure and compare token usage before/after prompt optimization.
Run this to verify token savings.

Usage:
    python measure_token_usage.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.ai_grading_service import AIGradingService


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation.
    Rule of thumb:
    - English: ~4 chars/token
    - Vietnamese: ~2.5 chars/token
    - Code (Python): ~3 chars/token
    - Mixed: ~3 chars/token (average)
    """
    return max(1, len(text) // 3)


def analyze_prompt():
    """Analyze the current prompt size and estimate token usage."""
    service = AIGradingService(ai_provider=None, repository=None)
    prompt_template = service._prompt

    # Sample data for estimation
    sample_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    n = int(input())
    print(fibonacci(n))
""".strip()

    sample_ast = """
Algorithms: recursion, fibonacci
Complexity: O(2^n)
AST Score: 7.5
Issues:
  - Exponential time complexity, should use memoization
  - No input validation
"""

    sample_rubric = """
Rubric:
1. Correctness (max 4.0)
   → Output matches expected results for all test cases
2. Algorithm (max 3.0)
   → Uses appropriate DSA technique
3. Code Quality (max 2.0)
   → Clean, readable, well-structured code
4. Complexity (max 1.0)
   → Efficient time and space complexity
"""

    # Build full prompt with sample data
    full_prompt = prompt_template.format(
        topic="fibonacci",
        filename="fibonacci.py",
        code=sample_code,
        ast_report=sample_ast,
        rubric_context=sample_rubric,
    )

    # Analyze components
    components = {
        "System prompt (template)": len(prompt_template),
        "Sample code": len(sample_code),
        "AST report": len(sample_ast),
        "Rubric context": len(sample_rubric),
        "TOTAL (with sample data)": len(full_prompt),
    }

    print("=" * 70)
    print("AI Token Usage Analysis")
    print("=" * 70)
    print()
    print("Component Breakdown:")
    print("-" * 70)
    for name, chars in components.items():
        print(f"  {name:40s} {chars:6,} chars  ~{estimate_tokens(str(chars)):5,} tokens")

    print()
    print("-" * 70)
    print(f"  {'TOTAL PROMPT':40s} {len(full_prompt):6,} chars  ~{estimate_tokens(full_prompt):5,} tokens")
    print()

    # Compare with original
    original_prompt_chars = 2200  # Original system prompt
    original_code_limit = 15000   # Original code limit
    original_est_tokens = (original_prompt_chars + original_code_limit) // 3

    current_prompt_chars = len(prompt_template)
    current_code_limit = 8000     # New code limit
    current_est_tokens = (current_prompt_chars + current_code_limit) // 3

    savings_chars = original_est_tokens - current_est_tokens
    savings_pct = (savings_chars / original_est_tokens) * 100

    print("Comparison (average case with full code):")
    print("-" * 70)
    print(f"  {'BEFORE optimization':40s} ~{original_est_tokens:5,} tokens")
    print(f"  {'AFTER optimization':40s}  ~{current_est_tokens:5,} tokens")
    print(f"  {'SAVINGS':40s}    ~{savings_chars:5,} tokens ({savings_pct:.0f}%)")
    print()

    # Cost estimation
    cost_per_1k_tokens = 0.000375  # Gemini 1.5 Flash input pricing
    cost_before = original_est_tokens / 1000 * cost_per_1k_tokens
    cost_after = current_est_tokens / 1000 * cost_per_1k_tokens

    print("Cost per API call (Gemini 1.5 Flash input):")
    print("-" * 70)
    print(f"  Before: ${cost_before:.6f}")
    print(f"  After:  ${cost_after:.6f}")
    print(f"  Save:   ${cost_before - cost_after:.6f} per call")
    print()

    # Annual savings estimate
    calls_per_day = 100
    calls_per_year = calls_per_day * 365
    annual_savings = (cost_before - cost_after) * calls_per_year

    print(f"Estimated annual savings ({calls_per_day} submissions/day):")
    print("-" * 70)
    print(f"  Total API calls/year: {calls_per_year:,}")
    print(f"  Annual savings:       ${annual_savings:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    analyze_prompt()
