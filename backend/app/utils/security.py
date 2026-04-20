"""
DSA AutoGrader - Security Utilities.

Code safety checking and fingerprint generation.
"""

import ast
import hashlib
from typing import Dict, List, Set


class PythonSafetyChecker:
    """Checks Python code for dangerous patterns."""

    DANGEROUS_IMPORTS = {
        "os",
        "sys",
        "subprocess",
        "socket",
        "urllib",
        "http",
        "requests",
        "aiohttp",
        "shutil",
        "pathlib",
        "io",
        "multiprocessing",
        "threading",
        "concurrent",
        "ctypes",
        "cffi",
        "pickle",
        "marshal",
        "shelve",
    }

    DANGEROUS_FUNCTIONS = {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
        "globals",
        "locals",
        "vars",
        "dir",
        "input",
        "setattr",
        "getattr",
        "delattr",
    }

    def check(self, code: str) -> List[Dict]:
        """
        Check code for safety violations.

        Returns list of violations found.
        """
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return [{"type": "syntax_error", "message": "Invalid Python syntax"}]

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in self.DANGEROUS_IMPORTS:
                        violations.append(
                            {
                                "type": "dangerous_import",
                                "module": module,
                                "line": node.lineno,
                                "message": f"Dangerous import: {module}",
                            }
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in self.DANGEROUS_IMPORTS:
                        violations.append(
                            {
                                "type": "dangerous_import",
                                "module": module,
                                "line": node.lineno,
                                "message": f"Dangerous import from: {module}",
                            }
                        )

            elif isinstance(node, ast.Call):
                # Check dangerous function calls
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_FUNCTIONS:
                        violations.append(
                            {
                                "type": "dangerous_function",
                                "function": node.func.id,
                                "line": node.lineno,
                                "message": f"Dangerous function: {node.func.id}()",
                            }
                        )

        return violations


class ComplexityAnalyzer:
    """Analyzes code complexity."""

    def analyze(self, code: str) -> Dict:
        """Analyze code complexity."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"time_complexity": "O(unknown)", "space_complexity": "O(unknown)"}

        max_nesting = 0
        max_loop_depth = 0

        def get_depths(node, current_nesting=0, current_loop_depth=0):
            nonlocal max_nesting, max_loop_depth
            
            is_nesting_node = isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.FunctionDef, ast.ClassDef))
            is_loop_node = isinstance(node, (ast.For, ast.While))
            
            new_nesting = current_nesting + (1 if is_nesting_node else 0)
            new_loop_depth = current_loop_depth + (1 if is_loop_node else 0)
            
            max_nesting = max(max_nesting, new_nesting)
            max_loop_depth = max(max_loop_depth, new_loop_depth)
            
            for child in ast.iter_child_nodes(node):
                get_depths(child, new_nesting, new_loop_depth)

        get_depths(tree)

        # Estimate complexity
        if max_loop_depth == 0:
            time_complexity = "O(1)"
        elif max_loop_depth == 1:
            time_complexity = "O(n)"
        else:
            time_complexity = f"O(n^{max_loop_depth})"

        return {
            "time_complexity": time_complexity,
            "space_complexity": "O(n)",
            "loop_count": max_loop_depth, # Renamed internally but keeping key for compatibility
            "nesting_depth": max_nesting,
        }


class FingerprintGenerator:
    """Generates code fingerprints using Token-level Winnowing."""

    def __init__(self, kgram_size: int = 5, window_size: int = 4):
        self.kgram_size = kgram_size
        self.window_size = window_size

    def generate(self, code: str) -> str:
        """Generate AST winnowing fingerprint."""
        try:
            tree = ast.parse(code)
            tokens = self._extract_tokens(tree)
            if not tokens:
                return ""

            kgrams = self._get_kgrams(tokens)
            fingerprints = self._winnow(kgrams)
            return "|".join(map(str, fingerprints))
        except Exception:
            # Fallback to simple hash for unparseable code
            normalized = "".join(code.split())
            return hashlib.md5(normalized.encode()).hexdigest()

    def _extract_tokens(self, node: ast.AST) -> List[int]:
        """Extract sequential AST node types as integer tokens."""
        tokens = []
        for n in ast.walk(node):
            node_type = type(n).__name__
            tokens.append(hash(node_type) & 0xFFFFFFFF)
        return tokens

    def _get_kgrams(self, tokens: List[int]) -> List[int]:
        """Generate k-gram hashes from tokens."""
        n = len(tokens)
        if n < self.kgram_size:
            return [hash(tuple(tokens)) & 0xFFFFFFFF] if tokens else []

        kgrams = []
        for i in range(n - self.kgram_size + 1):
            kgram = tuple(tokens[i : i + self.kgram_size])
            kgrams.append(hash(kgram) & 0xFFFFFFFF)
        return kgrams

    def _winnow(self, kgrams: List[int]) -> Set[int]:
        """Apply robust winnowing (sliding window) minimum algorithm."""
        fingerprints = set()
        n = len(kgrams)

        if n <= self.window_size:
            return set(kgrams)

        for i in range(n - self.window_size + 1):
            window = kgrams[i : i + self.window_size]
            # Pick minimum hash to guarantee robust matching across gaps
            fingerprints.add(min(window))

        return fingerprints


def calculate_jaccard_similarity(set1: Set, set2: Set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 and not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


# Convenience functions
def check_python_safety(code: str) -> List[Dict]:
    """Check code safety."""
    checker = PythonSafetyChecker()
    return checker.check(code)


def generate_code_fingerprint(code: str) -> str:
    """Generate code fingerprint."""
    gen = FingerprintGenerator()
    return gen.generate(code)


def calculate_code_similarity(code1: str, code2: str) -> float:
    """Calculate code similarity."""
    fp1 = set(generate_code_fingerprint(code1).split("|"))
    fp2 = set(generate_code_fingerprint(code2).split("|"))
    return calculate_jaccard_similarity(fp1, fp2)
