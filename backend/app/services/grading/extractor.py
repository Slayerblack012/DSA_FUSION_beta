"""
DSA AutoGrader - AST Feature Extractor.

Walks the AST and populates a ``CodeFeatures`` instance.
Uses Visitor pattern for clean traversal.
"""

import ast

from app.services.grading.constants import SCORING_CONSTANTS, CodeFeatures


class ASTFeatureExtractor(ast.NodeVisitor):
    """Extracts features from AST for algorithm detection."""

    def __init__(self) -> None:
        self.features = CodeFeatures()
        self._current_depth = 0
        self._current_loop_depth = 0

    def extract(self, tree: ast.AST) -> CodeFeatures:
        """Extract all features from *tree*."""
        self._visit_node(tree)
        self._post_process()
        return self.features

    def _visit_node(self, node: ast.AST, depth: int = 0, loop_depth: int = 0) -> None:
        """Visit node and update features."""
        self._update_depth_metrics(depth, loop_depth)
        self._update_fingerprint(node)
        self._extract_node_features(node)

        for _field_name, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self._visit_child(item, depth, loop_depth)
            elif isinstance(value, ast.AST):
                self._visit_child(value, depth, loop_depth)

    def _visit_child(self, node: ast.AST, depth: int, loop_depth: int) -> None:
        """Visit a child node with updated depth metrics."""
        is_loop = isinstance(node, (ast.For, ast.While))
        new_loop_depth = loop_depth + 1 if is_loop else loop_depth
        new_depth = depth + 1 if isinstance(node, (ast.For, ast.While, ast.FunctionDef, ast.If)) else depth
        self._visit_node(node, new_depth, new_loop_depth)

    def _update_depth_metrics(self, depth: int, loop_depth: int) -> None:
        """Update nesting and loop depth metrics."""
        self.features.node_count += 1
        self.features.max_nesting = max(self.features.max_nesting, depth)
        self.features.max_loop_depth = max(self.features.max_loop_depth, loop_depth)

    def _update_fingerprint(self, node: ast.AST) -> None:
        """Update fingerprint with node type (excluding Load/Store contexts)."""
        if not isinstance(node, (ast.Load, ast.Store)):
            self.features.nodes_for_fingerprint.append(type(node).__name__)

    def _extract_node_features(self, node: ast.AST) -> None:
        """Extract features specific to node type."""
        # Imports
        if isinstance(node, ast.Import):
            for n in node.names:
                self.features.imports.add(n.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            self.features.imports.add(node.module)

        # Data structures
        elif isinstance(node, (ast.List, ast.ListComp)):
            self.features.has_list = True
        elif isinstance(node, ast.Tuple):
            self.features.has_tuple = True
        elif isinstance(node, (ast.Set, ast.SetComp)):
            self.features.has_set = True
        elif isinstance(node, (ast.Dict, ast.DictComp)):
            self.features.has_dict = True

        # Control flow
        elif isinstance(node, (ast.For, ast.While)):
            self.features.loop_count += 1
            if isinstance(node, ast.While):
                self.features.has_while_loop = True
        elif isinstance(node, ast.If):
            self.features.if_count += 1
        elif isinstance(node, ast.Return):
            self.features.has_returns = True
        elif isinstance(node, ast.Compare):
            self.features.comparison_count += 1
        elif isinstance(node, ast.Yield):
            self.features.has_yield = True
        elif isinstance(node, ast.Lambda):
            self.features.has_lambda = True

        # Advanced features - delegate to specific handlers
        elif isinstance(node, ast.Subscript):
            self._check_subscript_features(node)
        elif isinstance(node, ast.ListComp):
            self._check_list_comp_features(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            self._check_assignment_features(node)
        elif isinstance(node, ast.ClassDef):
            self.features.has_class = True
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            self.features.class_attrs.add(node.attr)
            if node.attr == "prev":
                self.features.has_prev = True
        elif isinstance(node, ast.BinOp):
            self.features.has_binary_op = True
            self._check_binary_op_features(node)
        elif isinstance(node, ast.Call):
            self._check_call_features(node)
        elif isinstance(node, ast.FunctionDef):
            self._check_function_features(node)
        elif isinstance(node, ast.AnnAssign):
            self.features.has_type_hints = True
        elif isinstance(node, ast.Name):
            self._check_name_features(node)

    def _check_subscript_features(self, node: ast.Subscript) -> None:
        """Check for slicing and matrix access patterns."""
        if isinstance(node.slice, ast.Slice):
            self.features.has_slicing = True
        if isinstance(node.value, ast.Subscript):
            self.features.has_matrix_access = True
            if isinstance(node.value.value, ast.Subscript):
                self.features.has_3d_array_access = True

    def _check_list_comp_features(self, node: ast.ListComp) -> None:
        """Check for list comprehension with filter (Quick Sort indicator)."""
        for gen in node.generators:
            if gen.ifs:
                self.features.has_list_comp_filter = True
                break

    def _check_assignment_features(self, node) -> None:
        """Check for swap operations and global variables."""
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
            if len(node.targets[0].elts) == 2:
                self.features.has_swap = True
        if self._current_depth == 0 and self._is_non_constant_assignment(node):
            self.features.global_var_count += 1

    def _is_non_constant_assignment(self, node) -> bool:
        """Check if assignment is non-constant (not UPPER_CASE)."""
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.isupper():
                    return True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.isupper():
                return True
        return False

    def _check_binary_op_features(self, node: ast.BinOp) -> None:
        """Check for division by 2 (Binary Search indicator)."""
        if isinstance(node.op, (ast.FloorDiv, ast.RShift)):
            if isinstance(node.right, ast.Constant) and node.right.value == 2:
                self.features.has_div2 = True

    def _check_call_features(self, node: ast.Call) -> None:
        """Check for pop() and deque() calls."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
            self.features.has_pop = True
        elif isinstance(node.func, ast.Name) and node.func.id == "deque":
            self.features.has_deque = True
        elif isinstance(node.func, (ast.Name, ast.Attribute)):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            
            if name in ["sort", "sorted", "heappush", "heappop"]:
                self.features.has_greedy_pattern = True

    def _check_function_features(self, node: ast.FunctionDef) -> None:
        """Check for long functions and recursion."""
        if len(node.body) > SCORING_CONSTANTS.FUNCTION_MAX_LINES:
            self.features.long_func_count += 1
        if node.returns:
            self.features.has_type_hints = True
        
        recursive_calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == node.name:
                    recursive_calls.append(child)
        
        if recursive_calls:
            self.features.has_recursion = True
            if len(recursive_calls) >= 2:
                self.features.is_divide_conquer = True

    def _check_name_features(self, node: ast.Name) -> None:
        """Check for DP variable naming patterns."""
        name = node.id.lower()
        dp_patterns = ["dp", "memo", "table", "cache", "f", "opt"]
        if any(pattern in name for pattern in dp_patterns):
            self.features.has_dp_var = True

    def _post_process(self) -> None:
        """Post-processing after AST traversal."""
        if "collections" in self.features.imports:
            self.features.has_deque = True
        if self.features.max_loop_depth >= 2:
            self.features.has_nested_loops = True
